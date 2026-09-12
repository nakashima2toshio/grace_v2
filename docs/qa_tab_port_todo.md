# 「② Q/A 作成」タブ 移植 TODO（grace_v2_local → grace_v2）

**目的**: `./run_dev.sh` の「データ管理」タブに **② Q/A 作成** サブタブを追加し、
チャンク化 → Q/A 生成 → Qdrant 登録の 3 工程を**画面から通しで実行できる**ようにする。

| | |
|---|---|
| 移植元 | `grace_v2_local` master（`_qa_runner` / `QaGenerationParams` / サブタブ ②） |
| 移植先 | `grace_v2` master（`d5a697f`） |
| 作成日 | 2026-09-12 |

> **✅ 2026-09-12 に V1〜V6 を実装済み。** 本書は着手時の調査記録として残す。
> §3 の 3 点は推奨（A / 直接起動コマンド / 素の入力・`claude-sonnet-4-6`）どおりに実装した。
> 現在の設計は [`backend/docs/data_pipeline.md`](../backend/docs/data_pipeline.md)（v1.2 以降）を参照。
>
> **本書の記述は TODO と調査結果のみ。**
> 記載した差分は 2026-09-12 に両リポジトリの実ファイルを `diff -u` して確認したもの。

---

## 0. 現在地（調査でわかったこと）

### 0-1. grace_v2 には Q/A 生成の UI が無い

`backend/app/core/data_jobs.py` の末尾で登録される runner は **3 種**:

```python
register_runner(ChunkingParams, _chunking_runner, "chunking")
register_runner(RegisterParams,  _register_runner, "register")
register_runner(DeleteParams,    _delete_runner,   "delete")
```

`POST /api/qdrant/register` の入力は「**既に作られた Q/A CSV**」である。
その一段手前（チャンク済み CSV → Q/A CSV）は CLI
（`qa_qdrant/make_qa_register_qdrant.py` の Phase 1）にしか無く、
**画面だけではパイプラインが途中で切れている**。

`grace_v2_local` は 2026-09-05 にここを埋め、runner は 4 種（`qa` を追加）になっている。

### 0-2. 土台は揃っている ＝ これは「移植」であって新規実装ではない

| 必要なもの | grace_v2 の状況 |
|---|---|
| `qa_generation/pipeline.py::QAPipeline` | ✅ **ある**。local との差分は既定モデル 1 行だけ（`run()` の引数は完全一致） |
| `qa_generation/smart_qa_generator.py` | ✅ ある。`create_llm_client(provider="anthropic", ...)` で正しい |
| Celery 経路（`celery_tasks.py` / `celery_config.py`） | ✅ ある（⚠️ `start_celery.sh` は**無い** → §3-2） |
| `ALLOWED_INPUT_DIRS` に `output_chunked` | ✅ ある（Q/A 生成の入力ディレクトリ） |
| ジョブ基盤（`core/jobs.py` / SSE / HITL） | ✅ ある。`chunking` と同じ器に載る |
| `DataPanel` / `DataJobPanel` / `dataReducer` | ✅ ある。`variant` / `kind` を 1 つ増やす形 |

つまり **`QAPipeline` を同期ラッパー経由でジョブ基盤に載せ、UI の分岐を 1 本足す**だけである。

### 0-3. 差分の全体像（local にあって grace_v2 に無いもの）

| 層 | ファイル | 追加されるもの |
|---|---|---|
| service | `services/data_pipeline_service.py` | `run_qa_generation_sync()` |
| core | `backend/app/core/data_jobs.py` | `QaGenerationParams` / `QA_STEP_IDS` / `QA_STEP_LABELS` / `_qa_runner` / `register_runner(..., "qa")` |
| schema | `backend/app/schemas.py` | `QaGenerationRequest` |
| API | `backend/app/api/data.py` | `POST /api/qa/generate` |
| 型 | `frontend/src/types.ts` | `QaParams` / `DataJobKind` に `'qa'` / `DataJobResult` に Q/A 系フィールド |
| API client | `frontend/src/api/client.ts` | `startQaGeneration()` |
| 純関数 | `frontend/src/state/dataParams.ts` | `QaFormState` / `buildQaParams()` / `canSubmitQa()` |
| 純関数 | `frontend/src/state/dataReducer.ts` | `QA_STEP_IDS` / `QA_STEP_LABELS` ＋ `stepIdsFor` / `stepLabelsFor` の分岐 |
| UI | `frontend/src/components/DataPanel.tsx` | サブタブ ②（既存 ②③ は ③④ へ繰り下げ） |
| UI | `frontend/src/components/DataJobPanel.tsx` | `variant='qa'` のフォーム・バッジ・結果表示 |

---

## 1. ⚠️ 移植しないもの（持ち込むと壊れる／意味が無い）

`grace_v2` と `grace_v2_local` は**双方向に乖離している**（CLAUDE.md §5）。
local 側の該当ファイルには、Q/A タブとは**無関係な local 専用の変更**が同居している。
**ファイル単位のコピーは禁止。以下は持ち込まない。**

| local にあるもの | 持ち込まない理由 |
|---|---|
| `components/ModelSelect.tsx` / `state/modelLabel.ts` | grace_v2 に**存在しない**。依存する `GET /api/models` `GET /api/model` も無い（`api/meta.py` は `verticals` / `rulesets` / `health` のみ） |
| `_resolve_model()`（`grace_config.yml` から既定モデルを解決） | Ollama で `.env` と `grace_config.yml` の既定が割れた事故への対処。Anthropic 版には該当する食い違いが無い |
| `ollama_unreachable_message()` / `model_not_pulled_message()` / `list_pulled_ollama_models()` | ローカル LLM 固有の事前チェック。Anthropic 版は **`ANTHROPIC_API_KEY` ガード**が同じ役割を果たす |
| `config.py::get_default_chunking_workers()` / `DEFAULT_CHUNKING_WORKERS = 1` | Ollama が既定で直列実行することへの対処。Anthropic API は並列で回るので **`workers: 8` のままにする** |
| `done_event()` / `created_at` / `finished_at` / `state/serverTiming.ts` | サーバ時計から所要時間を出す**別機能**。Q/A タブとは独立 → §5 の別タスクへ |
| `ChunkingAbortedError` の捕捉 | local の chunking 側の改修。grace_v2 の `chunking/` に**この例外は存在しない** → §5 |

**逆に、grace_v2 にしか無いもの（`formMemory` / `metaFetch` / `timelineAnnounce` /
`MetaErrorBanner`）を消さないこと。** 今回触る 4 ファイルは直接は関係しないが、
差分を当てる際に必ず `diff -u` で確認する。

---

## 2. タスク

### V1. `services/data_pipeline_service.py` に `run_qa_generation_sync()` を追加

- `QAPipeline` の同期ラッパー。**パイプライン本体には手を入れない**（CLI と結果を一致させるため）
- 引数: `input_file` / `model` / `output_dir` / `max_docs` / `use_celery` / `concurrency` / `batch_chunks` / `analyze_coverage`
- 戻り値: `QAPipeline.run()` の戻り値そのまま（`saved_files` / `qa_count` / `coverage_results` / `success`）
- `from qa_generation.pipeline import QAPipeline` は**関数内の遅延 import**（コレクション一覧など
  この関数を通らない経路に celery / LLM クライアントの import コストを払わせない。既存の
  `run_chunking_sync()` と同じ方針）
- ⚠️ `run_chunking_sync()` と違い **`asyncio.run()` は挟まない**。`QAPipeline.run()` は同期関数で、
  並列化は Celery か `ThreadPoolExecutor` の中に閉じている
- ⚠️ `celery_workers=1` は**ワーカー数のチェック用**。実際の並列数は `concurrency` が決める

**受け入れ条件**: 既存の `run_chunking_sync()` と並ぶ位置に置かれ、docstring に上記 2 つの ⚠️ が入っている。

### V2. `backend/app/core/data_jobs.py` に Q/A ジョブの runner を追加

- `QaGenerationParams`（dataclass）
  - `input_file` / `output_dir="qa_output"`（→ §3-1 で決める） / `model="claude-sonnet-4-6"` /
    `max_docs` / `use_celery=False` / `concurrency=8` / `batch_chunks=3` / `analyze_coverage=True` / `verbose=False`
- `QA_STEP_IDS = ("load", "generate", "coverage", "save")` と `QA_STEP_LABELS`
  （① チャンク済み CSV の読み込み / ② Q/A ペア生成 / ③ カバレージ分析（任意） / ④ Q/A CSV・JSON 出力）
- `_qa_runner(params, emit, confirm)`
  - **`confirm` は使わない**（非破壊。出力はタイムスタンプ付きの新規ファイル）
  - `ANTHROPIC_API_KEY` 未設定なら即 error（`_chunking_runner` と同じ形）
  - **① で入力を検証しきる**: 拡張子が `.csv` でなければ error、
    `pd.read_csv(path, nrows=1)` でカラムを見て `text` / `Combined_Text` / `content` / `chunk_text` が
    1 つも無ければ error。
    ⚠️ `QAPipeline` は読み込み後に `ValueError` を投げるため、放っておくと
    「LLM を呼ぶ前に分かる誤り」が**生成ステップの失敗**として見えてしまう
  - ② は `capture_logs(emit, step="generate")` で囲み、生成後に `handler.set_step()` で
    以降のログを `coverage` / `save` へ寄せる
  - **`qa_count == 0` は error にする**（例外は出ていないが 1 件も作れていない＝後続の登録が空振りする）
  - `use_celery=True` で失敗したときは、エラーメッセージにワーカー起動の示唆を足す（§3-2 の文言）
  - `analyze_coverage=False` のときは `coverage` を `step_skipped`
  - 戻り値: `{"kind": "qa", "input_file", "qa_csv", "qa_json", "qa_count", "coverage_rate", "total_chunks", "model"}`
- 末尾に `register_runner(QaGenerationParams, _qa_runner, "qa")` を追加（`chunking` と `register` の間）

**受け入れ条件**: `test_runner_is_registered` に `qa` の行を足して通る。

### V3. スキーマと API エンドポイント

- `backend/app/schemas.py` に `QaGenerationRequest`
  - `input_file`（`min_length=1`） / `output_dir` / `model` / `max_docs`（`ge=1`） /
    `use_celery` / `concurrency`（`ge=1, le=32`） / `batch_chunks`（`ge=1, le=20`） /
    `analyze_coverage` / `verbose`
  - ⚠️ local の `_validate_model_choice`（`get_selectable_ollama_models()` 照合）は**持ち込まない**。
    grace_v2 にその関数も `/api/models` も無い
- `backend/app/api/data.py` に `POST /api/qa/generate`（`status_code=202` / `response_model=QueryAccepted`）
  - 承認は発生しない。入力検証は runner 側（`/api/chunking/run` と同じ責務分担）
- `DataJobStatusResponse` の docstring を `chunking / qa / register / delete` に更新
- モジュール docstring の表・「3 種」→「4 種」を更新（`api/data.py` / `core/data_jobs.py`）

### V4. フロントの型・API クライアント・純関数

- `types.ts`
  - `QaParams`（`model` は必須。→ §3-3）
  - `DataJobKind` に `'qa'` を追加
  - `DataJobResult` に `qa_csv` / `qa_json` / `qa_count` / `coverage_rate` / `total_chunks` を追加（すべて optional）
- `api/client.ts` に `startQaGeneration(params)`（`POST /api/qa/generate`）
- `state/dataParams.ts` に `QaFormState` / `buildQaParams()` / `canSubmitQa()`
  - `output_dir` が空白なら既定へ、`max_docs` は空欄 → `null`（既存の `toOptionalString` / `toOptionalNumber` を使う）
- `state/dataReducer.ts` に `QA_STEP_IDS` / `QA_STEP_LABELS` と `stepIdsFor` / `stepLabelsFor` の `case 'qa'`

**受け入れ条件**: `dataParams.test.ts` / `dataReducer.test.ts` に Q/A のケースを追加して `npm test` が通る。

### V5. UI（サブタブとフォーム）

- `DataPanel.tsx`
  - `SubTab` に `'qa'` を追加し、**① チャンキング → ② Q/A 作成 → ③ Qdrant 登録 → ④ コレクション管理**へ
  - 既存 2 つのラベルの丸数字を ③ ④ へ繰り下げる（**ここを忘れると番号が重複する**）
- `DataJobPanel.tsx`
  - `DataJobVariant` に `'qa'`、`DEFAULT_DIR` に `qa: 'output_chunked'`
  - Q/A 用の state（`qaOutputDir` / `useCelery` / `concurrency` / `batchChunks` / `analyzeCoverage`。
    `model` と `maxDocs` は既存を共用）
  - フォーム: 出力ディレクトリ / モデル / 1 回の生成で渡すチャンク数 / 最大チャンク数 /
    トグル（カバレージ分析・Celery・詳細ログ）/ Celery ON のときだけ並列タスク数と注意書き
  - 送信ボタン: `Q/A を生成`
  - Timeline バッジ: `load` の `text_column`、`generate` の `qa_count` と `model`、`coverage` の `coverage_rate`
  - 結果: 生成 Q/A ペア数 / カバレージ率 / 入力チャンク数 / Q/A CSV パス
  - 末尾の notice: 「入力は**チャンク済み CSV**（① の出力）。生成された Q/A CSV はそのまま ③ の入力になる」
  - ⚠️ `submit` の依存配列に `qaState` を足す

### V6. テスト・ドキュメント・CI

**テスト（backend）** — local の `test_data_jobs.py` から Q/A 分を移植（local 側の関数名）:

| テスト | 何を守るか |
|---|---|
| `test_qa_runner_emits_four_steps` | ステップ ID が `load/generate/coverage/save` の 4 つ |
| `test_qa_runner_never_asks_for_confirmation` | 非破壊ジョブが承認を求めない |
| `test_qa_skips_coverage_when_disabled` | `analyze_coverage=False` で skip 扱い |
| `test_qa_rejects_non_csv_input` | 拡張子違いを ① で弾く |
| `test_qa_rejects_csv_without_text_column` | カラム不足を ① で弾く（LLM を呼ばない） |
| `test_qa_zero_pairs_is_error` | 0 件生成を成功にしない |
| `test_qa_celery_failure_mentions_worker` | Celery 失敗時にワーカー起動を示唆する |
| `test_qa_endpoint_validates_params` | 422 になる入力（`concurrency` 範囲外など） |
| （新規）`test_qa_requires_api_key` | `ANTHROPIC_API_KEY` 未設定で即 error（grace_v2 固有。local には無い） |

> ⚠️ local の `test_qa_default_model_is_resolved_at_run_time` /
> `test_qa_blank_model_falls_back_to_default` は `_resolve_model()` 前提なので**移植しない**。

**テスト（frontend）**: `buildQaParams` / `canSubmitQa` / `stepIdsFor('qa')` / `stepLabelsFor('qa')` /
`qa` ジョブの result 畳み込み。

**ドキュメント**（grace_v2 は local より backend/docs が厚い。以下は**すべて**追随が要る）:

| ファイル | 直すところ |
|---|---|
| `backend/docs/data_pipeline.md` | 工程表・エンドポイント表・サブタブの並び（「3 工程」「② Qdrant 登録」の記述） |
| `backend/docs/api_data.md` | エンドポイント一覧・IPO に `POST /api/qa/generate` を追加 |
| `backend/docs/core_data_jobs.md` | params 表・runner・ステップ定義に `qa` を追加 |
| `backend/docs/schemas.md` | `QaGenerationRequest` を追加 |
| `frontend/docs/DataPanel.md` | サブタブ 3 → 4 |
| `frontend/docs/DataJobPanel.md` | `variant` 2 → 3、Props・state・結果表示。**テスト件数は実行して実測値を書く** |
| `CLAUDE.md` §2 | 「データ準備（3段階）」に Web からも実行できる旨を追記するか判断（local は追記済み） |

**CI 4 ゲート**（CLAUDE.md §4）をローカルで通してから push:

```bash
uv run ruff check . --no-cache
uv run pytest backend/tests -q
python -m compileall -q -x '\.venv|/\.git/|/logs/' .
cd frontend && npm run lint && npm test && npm run build
```

---

## 3. 実装前に決めること（**local と同じにしない方がよい箇所**）

### 3-1. Q/A の出力先の既定 — `qa_output/pipeline` ではなく `qa_output` を推す

local の既定は `qa_output/pipeline`。しかし
`services/data_pipeline_service.py::list_input_files()` は `target.iterdir()` で
**サブディレクトリを見ない**。一方「③ Qdrant 登録」の既定ディレクトリは `qa_output` である。

→ **local の既定のままだと、② で作った CSV が ③ の選択肢に出ない。**
（入力ファイルは `<select>` で、自由入力できない。）

| 案 | 評価 |
|---|---|
| **A. 既定を `qa_output` にする**（推奨） | ② → ③ が画面だけで繋がる。`save_results()` は `output_dir` 直下に書くので 1 行の変更で済む |
| B. `list_input_files()` を再帰にする | ③ の選択肢に無関係なファイルが増える。許可ディレクトリの検証も見直しが要る |
| C. local に合わせ、画面に注意書きを出す | 「画面から通しで実行できる」という目的を果たさない |

> なお **A を採っても local との差は既定値 1 つだけ**で、パイプライン本体は同じ。

### 3-2. Celery の扱い — 機能は残す。ただし案内する**コマンドが違う**

`grace_v2` に **`start_celery.sh` は存在しない**（CLAUDE.md §9.4）。
local の UI 注意書き（`./start_celery.sh restart -c 8`）を**そのままコピーしてはいけない**。

grace_v2 で有効なのは直接起動:

```bash
celery -A celery_config worker --loglevel=info --concurrency=8 \
    -Q celery,high_priority,normal_priority,low_priority
```

（`qa_qdrant/docs/01_install.md` §5.3「方法2: 直接起動」。同ファイルの「方法1」は
リポジトリに無いスクリプトを案内しており、これ自体が別途の負債 → §5）

> **⚠️ 2026-09-12 追記・訂正。** 上の `01_install.md` §5.3「方法2」は
> **それ自体が誤っていた**（`-A celery_tasks` / `--queues=qa_generation`）。
> `qa_generation` は `Celery('qa_generation')` の**アプリ名**であってキュー名ではなく、
> `celery_config.py` が定義するキューは `celery` / `high_priority` /
> `normal_priority` / `low_priority` の 4 つである。この誤りを PR #129 で
> UI の注意書きへそのまま持ち込んでしまったため、後続 PR で是正した。
>
> **また §5 の判断も変更した**: `start_celery.sh` はリポジトリへ**移植した**
> （`celery_config.py` は両リポジトリでバイト単位に同一なのでドロップイン）。
> 現在の案内は `./start_celery.sh restart -c 8`。

### 3-3. モデル欄 — 素のテキスト入力のまま、既定は `claude-sonnet-4-6`

local は `ModelSelect`（`GET /api/models`）だが、grace_v2 にはその API もコンポーネントも無い。
**grace_v2 のチャンキングタブと同じ素の `<input>` に揃える。**

既定値は **`claude-sonnet-4-6`** とする（CLI `make_qa_register_qdrant.py` の `--model` 既定、
および `QAPipeline.__init__` の既定と一致させる。チャンキングの `claude-haiku-4-5` ではない —
Q/A 生成は文章生成の比重が大きい）。

---

## 4. 動作確認（CI とは別に、実データで 1 往復）

```bash
# 前提: .env に ANTHROPIC_API_KEY / GOOGLE_API_KEY、Qdrant 起動済み
./run_dev.sh            # backend :8000 + frontend :5173
```

1. 「データ管理」→「① チャンキング」で `OUTPUT/` の小さい CSV を `--max-rows` 相当の設定で流す
2. 「② Q/A 作成」で `output_chunked/` の出力を選び、**最大チャンク数 5** 程度で実行
   - ① 読み込み → ② 生成 → ③ カバレージ → ④ 出力 の 4 ステップが順に緑になること
   - 結果に「生成 Q/A ペア数」「カバレージ率」「Q/A CSV」が出ること
3. 「③ Qdrant 登録」で、**② の出力がファイル一覧に現れる**こと（§3-1 の確認）
4. 異常系: `.txt` を選ぶ／テキストカラムの無い CSV を選ぶ → **① の時点で**失敗すること
   （LLM を呼ばずに落ちる＝ログに生成の試行が出ない）

---

## 5. 本 TODO のスコープ外（local → grace_v2 の移植候補・別タスク）

今回の調査で見つかった、Q/A タブとは**独立**の差分。着手は別途判断する。

| 候補 | 内容 | 備考 |
|---|---|---|
| サーバ時計による所要時間 | `done_event()` / `created_at` / `finished_at` / `state/serverTiming.ts` / `useJobTiming` の `observeTiming` | SSE 未購読でも所要時間が出る。3 タブ共通の改善 |
| `ChunkingAbortedError` の握り | LLM 連続失敗をメッセージ付きで error にする | grace_v2 の `chunking/` に**この例外は無い**（`grep` で 0 件）。移植するなら例外の追加から |
| `qa_qdrant/docs/01_install.md` の `start_celery.sh` | リポジトリに無いスクリプトを「推奨」として案内している | §3-2 |
| `services/qa_service.py::run_advanced_qa_generation` | `import qa_generator_runner` するが **`qa_generator_runner.py` は存在しない**（呼ぶと確実に失敗する死にコード） | 削除可否の判断が要る |
| `services/docs/data_pipeline_service.md` | `services/docs/` に**この 1 本だけ無い**（両リポジトリとも） | §9.1 の IPO 形式で新規作成 |

---

## 6. 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-09-12 | 初版。両リポジトリの実ファイル差分に基づき作成（実装は含まない） |
