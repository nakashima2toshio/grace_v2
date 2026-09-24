# CLAUDE.md

このファイルは Claude Code（claude.ai/code）が本リポジトリで作業するときの指針です。

---

## ⚠️ ファイル書き込みポリシー

### GitHub ブランチ操作：全許可
- ブランチへのコミット・プッシュ・PR作成・master へのマージを確認なしで実行してよい。
- **指定ブランチ以外への push や force push は事前に確認すること。**

### ローカルファイル操作：作業範囲内許可
- タスクに関連するファイルの新規作成・編集は確認なしで実行してよい。
- タスクと無関係なファイルへの書き込みは事前に確認すること。
- **ファイルの削除など不可逆的な操作は事前に確認すること。**

---

## ⚠️ 作業原則（最重要）

- **必ずコードをよく読んでから判断する。** 「現状コード＋慎重さ」を優先して**読まずに**進めると、
  バグにバグを重ねることになる（実際にそれで 1 日溶かした事例あり）。
- 修正・調査の前に、関連する実コード（クライアント生成・既定モデル・呼び出し経路・
  プロバイダ解決）を実際に追って確認すること。「たぶん意図的」で確認を打ち切らない。
- **やっていない検証を「やった」と書かない。** テストが落ちたら落ちたと出力付きで報告する。
- 回帰修正を入れるときは、**修正前のコードに当ててテストが fail することを確認**する。
  fail しないテストは回帰を捕まえていない。

---

## 1. プロジェクト概要

**GRACE** — 業界特化・自律型エージェント基盤。日本語 RAG（Retrieval-Augmented Generation）に
根拠検証（groundedness）・Web 裏取り・HITL（Human-In-The-Loop）アクションを組み合わせる。

### ⚠️ エージェントは 2 つある

| エージェント | 情報の流れ | コア関数 | 画面 |
|---|---|---|---|
| **GRACE-Support** | 問い合わせ → **回答** | `backend/app/core/support_agent.py::run_support_agent_core` | 「基本版」「GRACE-Support」タブ |
| **GRACE-Review** | 文書 → **指摘** | `backend/app/core/review_agent.py::run_review_agent_core` | 「GRACE-Review」タブ |

**Support だけ見て作業しない。** `backend/tests` の約 1/3（58 ファイル中 18 ファイル）が
Review 系である。中核部品（`GroundednessVerifier` / `InterventionBridge` /
`support_actions.py` の `ActionBackend`）は**両者で共用**しているので、
Support のつもりで触った変更が Review を壊す。

| 層 | 実体 |
|---|---|
| フロントエンド | `frontend/` — Vite + React 18 + TypeScript（dev: `:5173`） |
| Web API | `backend/app/` — FastAPI（dev: `:8000`）。SSE でステップ進捗を配信 |
| Support コア | `backend/app/core/support_agent.py`、ゲートは `core/gates.py`、業界定義は `core/verticals.py` |
| Review コア | `backend/app/core/review_agent.py`、ゲートは `core/review_gates.py`、ルール定義は `core/rulesets.py` |
| 自律エージェント基盤 | `grace/` — planner / executor / confidence / intervention / replan / tools |
| ツール・検索 | `agent_tools.py`, `qdrant_client_wrapper.py`（`agent_parallel_search.py` / `agent_cache.py` は **Legacy ReAct 経路専用**。Web 経路では未稼働・§9.4 の注記を参照） |
| アクション実行 | `support_actions.py`（`ActionBackend`。**Support / Review 共用**） |
| データ準備（CLI） | `chunking/`, `qa_generation/`, `qa_qdrant/` |
| データ準備（Web） | `backend/app/api/data.py` / `api/qdrant.py`、`backend/app/core/data_jobs.py`、`services/data_pipeline_service.py` |
| ベクトルDB | Qdrant（`docker-compose/docker-compose.yml`） |

### 画面は 4 タブ（`frontend/src/App.tsx`）

| タブ id | ラベル | 中身 |
|---|---|---|
| `basic` | 基本版 | `SupportPanel variant="basic"` — 業界プロファイル**セレクタを出さない** |
| `support` | GRACE-Support | `SupportPanel variant="vertical"` — 業界プロファイルを選ぶ |
| `review` | GRACE-Review | `ReviewPanel` — 文書 textarea → 指摘一覧（左右 2 ペイン） |
| `data` | データ管理 | `DataPanel` — チャンク化 / Q&A 作成 / Qdrant 登録 / コレクション管理 |

`basic` と `support` は**同じ `SupportPanel`** に `variant` を渡しているだけである
（別コンポーネントではない）。タブ切替はアンマウント方式。

### 業界プロファイル（vertical）— Support 用
`backend/app/core/verticals.py` に `gov` / `saas` / `ec` を定義。各プロファイルが
許可コレクション・エスカレーションキーワード・アクションマップ・閾値・プロンプト追記を持つ。

### ルールセット（ruleset）— Review 用
`backend/app/core/rulesets.py` に `ec_ad`（EC広告表示）を定義。`VerticalProfile` と役割は
似るが「1 プロファイル = N 個の検査ルール」を持つため**型を分けている**
（`RuleSet` / `RuleItem`）。現在 23 ルール（景表法 / 薬機法 / 特商法 / 社内方針）。
`GET /api/rulesets` と ① S1 の解決に使う。

### パイプライン 1 周（Support）
```
0-(A) 入力・質問分析（複数質問の検知 → 選択 → 再構成）
 → 0-(B) 業界プロファイル適用
 → ① Plan（planner）
 → ② Execute（内部RAG → reasoning）
 → ③ Confidence（GroundednessVerifier で根拠検証）
 → ④ 回答ゲート（＋強制エスカレ＋救済）
 → ⑤ Web フォールバック
 → ④' 情報なし回答の検知
 → ⑥ Action（本人確認 → HITL CONFIRM → 実行）
```
`support_rate = supported / (supported + contradicted)` — neutral は分母から除外する
（＝答えていない内容を減点しない）。

### パイプライン 1 周（Review）
`REVIEW_STEP_IDS` の順に実行する。番号は Support との**対応を示す呼称**であり、
実行順とは一致しない。
```
S1 ruleset   RuleSet 適用（検索スコープ・しきい値・重大リスク語）
 → ① segment  文書を検査単位へ分割（決定的・原文オフセット保持）
 → ② retrieve セグメントごとに規程を RAG 検索
 → ③ detect   二段判定で違反候補を検出
 → ④ ground   GroundednessVerifier で「指摘が規程で裏付けられるか」を検証
 → ④' suppress 誤検知抑止 + 救済
 → ⑥ web      法改正の裏取り（任意・信頼度を下げる方向にのみ使う）
 → ⑤ severity 重大度の確定（＋重大リスク語による強制 high）
 → ⑦ action   レポート → HITL CONFIRM → バックエンド実行
```
Review の新規実装は **Segment / Detect / Severity の 3 つだけ**で、
Retrieve・Ground・誤検知抑止・Action は Support と同じ機構の再利用である。
設計は `backend/docs/review_flow.md`。

> **⚠️ CLI 入口は Support / Review とも存在しない（2026-09-19 以降）。**
> 唯一の入口は Web API（`uvicorn backend.app.main:app` → `run_support_agent_core` /
> `run_review_agent_core`）である。かつて Support には CLI
> （`agent_support_example.py`）と S0〜S9 のステップ別トレース（`grace/step_trace/s*.py`）が
> あったが、いずれも機能確認用の薄いラッパだったため削除した（実装は git 履歴に残る）。
> 挙動確認は `./run_dev.sh` か `backend/tests/`（`test_support_agent_core.py` /
> `test_review_agent_core.py`）で行う。

---

## 2. 開発コマンド

### 起動
```bash
# 前提: .env に ANTHROPIC_API_KEY / GOOGLE_API_KEY、Qdrant 起動済み
docker-compose -f docker-compose/docker-compose.yml up -d

# 開発サーバ一括起動（backend :8000 + frontend :5173）
./run_dev.sh

# バックエンド単体
uvicorn backend.app.main:app --reload --port 8000
```

> ⚠️ **エージェント実行の CLI は無い。** `agent_support_example.py` と
> `grace/step_trace/s*.py` は 2026-09-19 に削除した（§1 の注記）。
> 挙動確認は `./run_dev.sh`（:5173）か `backend/tests/` で行う。
> 下の「データ準備」の CLI は現役である。

### データ準備（3段階）
```bash
# 1. チャンク化
python -m chunking.csv_text_to_chunks_text_csv

# 2-3. Q/A 生成 + Qdrant 登録
python qa_qdrant/make_qa_register_qdrant.py
#   登録のみ: python qa_qdrant/register_to_qdrant.py
```

上の 3 工程（チャンク化 → Q/A 生成 → Qdrant 登録）とコレクション管理は、
**アプリの「データ管理」タブ**からも実行できる（`./run_dev.sh` → :5173）。
サブタブは ① チャンキング / ② Q/A 作成 / ③ Qdrant 登録 / ④ コレクション管理。
CLI と同じ関数（`QAPipeline` など）を呼ぶので挙動は同一。
設計は `backend/docs/data_pipeline.md` を参照。

> `--resume` つきの大規模バッチは引き続き CLI の方が適している。

### 検証（CI と同じゲート）

**初回のみ**、テスト用の依存を入れる（`[project] dependencies` の 221 行は**入れない**。
テストはスタブベースで実行時依存を必要としない）:

```bash
uv venv
uv pip install -r requirements-test.txt   # CI と共有する唯一の正本（18 パッケージ）
```

```bash
uv run ruff check . --no-cache             # lint
uv run --no-sync pytest backend/tests -q -rs   # backend テスト
python -m compileall -q -x '\.venv|/\.git/|/logs/' .   # 構文ゲート
cd frontend && npm run lint && npm test && npm run build   # frontend
```

> ⚠️ **`--no-sync` を付ける。** 付けないと `uv run` が `pyproject.toml` の
> `[project] dependencies`（221 行・spacy/matplotlib 等を含む）で環境を同期し直し、
> `requirements-test.txt` で作った軽い環境が上書きされる。
>
> ⚠️ **`backend/tests` が import するパッケージを足したら `requirements-test.txt` に追記する。**
> CI（`.github/workflows/ci.yml`）はこのファイルを読むので、YAML 側を直す必要は無い。
> 理由と過去の事故例（`openai` が `tqdm` を落として無関係な PR が落ちた）は同ファイルの冒頭に書いてある。

> `pyproject.toml` に `pythonpath` 指定は無い。CI は素の `pytest` を使うので
> `PYTHONPATH=.` を env で与えている（`uv run` 経由ならプロジェクトルートが通るので不要）。
> `python backend/tests/x.py` を直接叩くと `ModuleNotFoundError: No module named 'backend'`
> になる → `uv run python -m backend.tests.x` を使う。

---

## 3. プロバイダ方針（恒久ルール）

| 用途 | プロバイダ | 既定 | APIキー |
|---|---|---|---|
| **Embedding（検索）のみ** | **Gemini** | `gemini-embedding-001`（3072次元） | `GOOGLE_API_KEY` |
| **それ以外の全 LLM 用途**（Q&A生成・Plan/Execute/Reasoning/Confidence/Replan/ReAct 等） | **Anthropic** | `claude-sonnet-5`（軽量 `claude-haiku-4-5-20251001`） | `ANTHROPIC_API_KEY` |

- LLM クライアントは `helper.helper_llm.create_llm_client("anthropic")` /
  `grace.llm_compat.create_chat_client`。
- `config.GeminiConfig` は **Embedding 用途（`EMBEDDING_MODEL` / `EMBEDDING_DIMS`）に限って**参照可。
- **Embedding 文脈の `provider="gemini"` / `GOOGLE_API_KEY` は正しい**ので変更しない。
- 本リポジトリは Gemini 由来コードから Anthropic へ移植した経緯があり、コードに残る
  Gemini 系の **LLM** 既定は「設計上の意図」ではなく **移植漏れ（負債）**とみなす。
  発見次第 Anthropic へ是正する。「現存コード＝意図」と推論しないこと。

### 3.1 ⚠️ モデル名の解決経路は 4 本ある

「既定モデルを変える」ときに 1 箇所だけ直すと**取り残しが出る**。
必ず 4 本とも確認すること。

| # | 経路 | 実体 | 誰が読むか |
|---|---|---|---|
| 1 | **設定ファイル（正）** | `config/grace_config.yml` の `llm.model` / `llm.light_model` | `grace/config.py::ConfigLoader` 経由で planner / reasoning / groundedness / ReAct |
| 2 | **モジュール定数** | `backend/app/core/verticals.py::INTENT_MODEL`（リテラル） | 判定系（意図分類・情報なし判定）。**yml を一切見ない** |
| 3 | **Python 定数** | `config.py::ModelConfig.DEFAULT_MODEL` | 上記以外（チャンキング・Q&A 生成など CLI 側） |
| 4 | **リクエスト単位の上書き** | UI のモデルセレクタ → `QueryRequest.model` / `ReviewRequest.model` → コアが `config.llm.model` を差し替え | その 1 リクエストの生成・推論・根拠検証・③ Detect |

**経路 4 は経路 1 を「そのリクエストだけ」上書きする**（`copy.deepcopy(get_config())` の
コピーに対して行うので、他のジョブへは漏れない）。選択肢は
`config.py::ModelConfig.SELECTABLE_MODELS`（= `get_selectable_models()`）の 1 箇所で決まり、
スキーマのバリデータ・`GET /api/models`・コアの再検証がすべてそこを読む。
**`light_model` は上書きしない**（判定系は軽量モデルのまま。理由は
`backend/docs/config_and_providers.md` §3.1）。

**経路 1 が正。** 経路 2 は `backend/app/core/gates.py::judge_model()` が
「config から解決できないときだけ `INTENT_MODEL` へフォールバックする」形に是正済みなので、
**`INTENT_MODEL` を直接使うコードを新たに書かない**こと（詳細は同関数の docstring）。
経路 1 と 2 は現在たまたま同じ値（`claude-haiku-4-5-20251001`）なので、
**取り残しはテストでは表面化しない**。

設定は yml → 環境変数（接頭辞 `GRACE_`）→ `GraceConfig`（pydantic）で検証、の 3 段。

> ⚠️ トップレベルの **`config.py`（モジュール）** と **`config/`（ディレクトリ）** は別物。
> `config/` に入っているのは `grace_config.yml` だけで、`import config` は `config.py` を指す。

### 3.2 実在するモデル名（勝手に「修正」しない）

`config.py::ModelConfig` が定義する 7 つはすべて実在し、**すべて正しい**。

| モデル名 | 用途 | UI の選択肢 |
|---|---|:--:|
| `claude-fable-5-1` | 最上位（難しい推論・長時間のエージェント処理） | ✅ |
| `claude-opus-5-5` | 上位（`claude-opus-5` の後継・単価も安い） | ✅ |
| `claude-sonnet-5` | **既定**（推論・生成） | ✅ |
| **`claude-haiku-4-5`** | 軽量。**日付なしエイリアス**。チャンキングの既定値 | ✅ |
| `claude-opus-5` | 旧上位（後方互換。`llm.heavy_model` 等の既存設定用） | ❌ |
| `claude-haiku-4-5-20251001` | 上記の日付指定。`llm.light_model` / `INTENT_MODEL` の値 | ❌ |
| `claude-sonnet-4-6` | 旧既定（後方互換。既存設定の読み込み用） | ❌ |

**`claude-haiku-4-5` を「日付が抜けている」と判断して書き換えないこと。**
意図的なエイリアスであり、`MODEL_PRICING` / `MODEL_LIMITS` にも 7 つとも登録されている。
これは R1（モデル名のマッピングを作らない）と同種の事故である。

> ⚠️ **「UI の選択肢 ❌」は「使えない」という意味ではない。** 下 3 つは有効な
> モデル名で、設定ファイルからは指定できる。**同じモデルが 2 行（日付あり／なし）
> 並ぶのを避けるため、また旧世代を選ばせないため、セレクタに出していないだけ**である
> （`ModelConfig.AVAILABLE_MODELS` ⊃ `SELECTABLE_MODELS`）。
>
> ⚠️ **モデル世代で API への送り方が違う。** `ModelConfig` の
> `NO_TEMPERATURE_MODELS`（temperature は 400）/ `ADAPTIVE_THINKING_MODELS`
> （`budget_tokens` は 400・`adaptive` を送る）/ `ALWAYS_THINKING_MODELS`
> （`{"type": "disabled"}` も 400）を `grace/llm_compat.py` と
> `helper/helper_llm.py` が読む。**選択肢にモデルを足すときはこの 3 表も確認する**
> （詳細は `backend/docs/config_and_providers.md` §3.1）。

### 3.3 調査済み・触らなくてよい残置コード

- `config.py::GeminiConfig.DEFAULT_MODEL = "gemini-2.5-flash"` と `AVAILABLE_MODELS` —
  **参照ゼロ**（リポジトリ全体 grep 済み）。クラス docstring に「後方互換」と明記されている。
  §3 の「Gemini 系 LLM 既定は負債」に**該当しない**（死んでいるので実害が無い）。
  毎回調べ直さないよう、ここに結論を残す。

---

## 4. CI と ブランチ運用

### 必須ゲートは 4 つ（すべて blocking）

| ジョブ | 内容 |
|---|---|
| `compile (syntax gate)` | `python -m compileall` |
| `ruff` | `ruff check .`（`ruff==0.12.11` 固定） |
| `pytest (backend)` | `pytest backend/tests -q -rs`（実 API キー・Qdrant 不要） |
| `frontend (tsc + vitest + build)` | `npm run lint` → `npm test` → `npm run build` |

`auto-merge` は `needs: [build, lint, backend-tests, frontend]`。4 つ緑になれば
`claude/*` ブランチの PR を Ready 化して master へマージする（`hold` ラベルで抑止）。

> ⚠️ **frontend ゲートを忘れない。** Python 側が全部緑でも `frontend/src/types.ts` の
> 型エラー 1 個でマージは止まる。バックエンドの API スキーマを変えたら
> `frontend/src/types.ts` も必ず追随させる。

### ruff 設定の要点

`[tool.ruff.lint.isort] known-first-party` にトップレベルモジュールを列挙している。
**新規トップレベルモジュールを足したらここにも追記する**（現在は `scripts` /
`qdrant_delete_collection` を含む全 20 個。`agent_support_example` は
2026-09-19 の削除にあわせて外した）。

> ⚠️ **この設定の効き目を過大評価しないこと（2026-09-13 実測）。**
> `known-first-party` を丸ごとコメントアウトして `ruff 0.12.11 check .` を回しても
> **All checks passed** だった。ruff の isort 分類は `src`（既定 `["."]`）を使った
> **ファイルシステム解決**が先に効くため、リポジトリ直下に実体があるモジュールは
> 設定が無くても first-party になる。site-packages の導入状況は見ていない。
>
> つまり「未設定だと I001 がローカル緑／CI 赤になる」という以前の記述は
> **本リポジトリでは再現しない**。この列挙は保険であって、I001 の原因ではない。
> **I001 が出たときに真っ先にこの設定を疑って時間を溶かさないこと。**
> まず `ruff check --no-cache` の実出力（どのファイルのどの import 順か）を読む。

> ⚠️ **ローカルの `ruff` が CI と同じ版とは限らない。**
> この環境の `ruff` は uv ツール管理で新しい版が入っていることがある
> （実測: `ruff --version` → 0.15.8）。CI ゲートを再現するなら版を固定して呼ぶ:
> ```bash
> uvx ruff@0.12.11 check . --no-cache
> ```

### ブランチ
- 開発は `claude/<topic>` ブランチ。**ドラフト PR** で作成（auto-merge が Ready 化する）。
- **指定ブランチの PR が既にマージ済みなら、そのブランチは使い回さない。**
  `git fetch origin master && git checkout -B <branch> origin/master` で作り直す。
- **リモート Git プロキシは ref 削除を 403 で拒否する。** `git push origin --delete` は
  この環境から実行できない → ブランチ削除は GitHub UI かユーザのローカルで行う。
  できない旨を正直に報告し、コマンドを提示すること。
- GitHub 操作は `mcp__github__*` MCP ツール（`gh` CLI はこの環境に無い）。
- **モデル識別子（`claude-opus-5` 等）をコミットメッセージ・PR 本文・コードコメントに
  書かない**（チャット返信のみ）。

---

## 5. 姉妹リポジトリ（grace_v2_local）との関係

### ⚠️ 双方向に乖離している。ファイル単位のコピーは壊れる

`grace_v2`（Anthropic 版）と `grace_v2_local`（Ollama 版）は同じ構造だが、
**両方向に片側だけの機能がある**。「local にある機能を持ってくる」つもりで
ファイルを丸ごとコピーすると、**こちらにしかない機能が消える**。

| 機能 | grace_v2 | grace_v2_local |
|---|:--:|:--:|
| `state/formMemory.ts`（タブ切替時の入力退避） | ✅ | ✅（2026-09-20 に移植） |
| `state/metaFetch.ts` / `state/timelineAnnounce.ts` | ✅ | ✅（2026-09-20 に移植） |
| `components/MetaErrorBanner.tsx` | ✅ | ✅（2026-09-20 に移植） |
| `state/documentLimit.ts`（文字数上限の判定・アナウンス文言） | ✅ | ✅（2026-09-20 に移植） |
| `state/modelLabel.ts` | ✅ | ✅（**中身は別物**） |
| `state/headerModel.ts`（モデル選択をヘッダーで行う。全タブ） | ✅（2026-09-23） | ✅（2026-09-23 に移植。**既定値の取り方が違う**） |
| `components/ModelSelect.tsx` | ❌（2026-09-23 に削除） | ❌（同日に削除） |
| `state/focusTrap.ts` / `state/selectionKeys.ts`（a11y） | ✅（2026-09-24 に移植） | ✅ |
| LLM プロバイダ | Anthropic | Ollama（ローカル） |

> この表は、**ファイル単位で見た両リポジトリの差分**である。
> 実測日: 2026-09-24（`frontend/src/` のファイル一覧を両リポジトリで突き合わせ、**ファイル集合は一致**した）。
> **ファイル名が同じでも中身が同じとは限らない。** とくに次の 2 つは別物なので、
> **コピーで持ち込まない**こと。
> - `modelLabel.ts` — こちらは Anthropic の単価つきラベル、local は Ollama の
>   `supports_tool_calls` / `notes` を畳み込むラベル
> - `headerModel.ts` — データ管理タブの既定値が、こちらは `ModelInfo.chunking_model` /
>   `qa_model`、local は `ModelInfo.model`（local の `ModelInfo` にはこの 2 項目が無い）
>
> 片側にしかないフロント資産を足したら、**この表にも 1 行足す**こと。

**実例（2026-08-25）**: 基本版タブの複数行入力を local から移植する際、
`QueryForm.tsx` を丸ごとコピーしていれば `formMemory`（外した dry-run が
タブ切替で ON へ復帰する不具合の修正・v1.1）が消えていた。
`ModelSelect` を持ち込めばビルドも壊れていた。

### 移植するときの手順

1. **必ず `diff -u` を取る。** どちらの方向に何が違うかを目で見る。
   ```bash
   diff -u grace_v2/frontend/src/components/X.tsx grace_v2_local/frontend/src/components/X.tsx
   ```
2. **目的の機能に関係する差分だけを足す。** ファイルを置き換えない。
3. 移植先にしかないモジュールの参照（import・呼び出し）が消えていないか grep で確認する。
4. 既存機能のテスト（例: `formMemory.test.ts`）が通ることで温存を担保する。

### ドキュメントは実装に遅れていることがある

`frontend/docs/*.md` や `<package>/docs/*.md` を移植元として参照する前に、
**そのドキュメントが実装に追随しているか確認する**。

**実例**: `grace_v2_local/frontend/docs/QueryForm.md` は Version 1.0 のまま、
複数行入力とモデルセレクタの **2 機能分**遅れていた（`useState` の個数も
「× 8」と書かれていたが実際は 9 個）。コピー元にできず、書き直しになった。

---

## 6. フロントエンドの純関数規約

### 判断ロジックは `frontend/src/state/` の純関数へ出す

`frontend/vite.config.ts` の vitest 設定は次のとおり:

```ts
test: {
  environment: 'node',
  include: ['src/**/*.test.ts'],   // ← .test.tsx は収集されない
}
```

`@testing-library/react` は未導入で、**コンポーネントのレンダリングテストは書けない**。
そのため「どう判断するか」をコンポーネント内に残すとテストできなくなる。

**判断を含むロジックは必ず `state/` 配下の純関数へ切り出す。**
React の型（`KeyboardEvent` 等）に直接依存させず、必要なフィールドだけを受ける
インターフェースを定義すると、node 環境のテストから素のオブジェクトを渡せる。

| モジュール | 切り出した判断 |
|---|---|
| `state/queryParams.ts` | 送信ペイロードの組み立て・基本版での vertical 固定・識別子の有無 |
| `state/submitKey.ts` | textarea の送信キー（Ctrl+Enter / ⌘+Enter・**IME 変換中は送信しない**） |
| `state/dataParams.ts` | データ準備フォームの入力 → API パラメータ組み立て（空欄・トリム・null 化・未選択モデルのキー省略） |
| `state/tabKeys.ts` | タブの矢印キー移動 |
| `state/formMemory.ts` | タブ切替時の入力退避と復元（モデルはヘッダー側が持つので含まない） |
| `state/headerModel.ts` | ヘッダーのモデルセレクタ（全タブ。データ管理タブは工程ごとに 2 つ）の並べ方・表示値・選択肢 |
| `state/interventionKind.ts` | 承認待ちが action（⑥ 実行承認）か question（0-(A) 主質問の選択）か |
| `state/documentLimit.ts` | 文字数上限の判定・表示文言・**アナウンス文言**（超過中は長さを含めず再読み上げを防ぐ） |
| `state/metaFetch.ts` | メタ取得失敗を対処可能な文言へ（silent failure を出さない） |
| `state/modelLabel.ts` | ヘッダーの見出し文字列・単価つき選択肢のラベル |
| `state/timelineAnnounce.ts` | 支援技術へ読み上げる 1 行の決定 |
| `state/focusTrap.ts` | `ConfirmModal` 内の Tab 移動先（端で巻き戻す。**Escape では閉じない**） |
| `state/selectionKeys.ts` | 指摘の選択キー（Enter / Space・IME 変換中は発火しない）と選択トグル |
| `state/citations.ts` / `highlight.ts` / `elapsed.ts` / `activeJobs.ts` | 表示用の派生値 |
| `state/jobReducer.ts` / `dataReducer.ts` / `reviewReducer.ts` | ジョブ状態の遷移 |

> `state/useJobTiming.ts` は**例外的にフック**（`useState` / `useEffect` を持つ）。
> ただし判断は持たず、`Date.now()` の取得と phase の決着検知だけを行い、
> **整形・比較は `elapsed.ts` の純関数**が受け持つ（テストは `elapsed.test.ts` /
> `serverTiming.test.ts` 側にある）。ここに分岐を足さないこと。

コンポーネント側に残すのは**入力の保持と描画だけ**にする。

### コンポーネントを触ったら docs も更新する

`frontend/docs/<Component>.md` は `.claude/skills/grace-agent-docs/a_react_page_md_format.md`
の形式に従う。**Props の TypeScript コードブロックは実装の逐語コピー**なので、
prop を 1 つ足すときは他の prop が欠けていないかも確認する
（一部だけ更新すると「一見完成しているが実は誤り」になる）。

**テスト件数は実行して実測値を書く。** 記憶で書かない。

---

## 7. Mermaidダイアグラム スタイル規約

### 7.1 構文バージョン
**PyCharm Pro v9 互換構文**を使用する。

- ノードラベルにバッククォートや markdown文字列（`` `text` ``）を使用しない
- 特殊文字を含むノードラベルは必ずダブルクォート（`"..."`）で囲む
- TS の総称型（`Record<StepId, StepState>` 等）は `<` `>` がタグ解釈されうるため、
  ダブルクォートで囲んだうえで可能なら `Record[StepId, StepState]` へ置換する

### 7.2 カラーテーマ（黒背景・白文字）— **必須**

| 要素 | 設定値 |
|---|---|
| ノード背景色 | `fill:#000` |
| ノードテキスト色 | `color:#fff` |
| ノード枠線色 | `stroke:#fff` |
| サブグラフ背景色 | `fill:#1a1a1a` |
| サブグラフテキスト色 | `color:#fff` |
| サブグラフ枠線色 | `stroke:#fff` |

### 7.3 flowchart / graph の実装パターン
```
flowchart TB
    subgraph Layer["レイヤー名"]
        NodeA["ノードA"]
        NodeB["ノードB"]
    end
    NodeA --> NodeB
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class NodeA,NodeB default
style Layer fill:#1a1a1a,stroke:#fff,color:#fff
```

**必須ルール:**
1. `classDef default fill:#000,stroke:#fff,color:#fff` を必ずブロック末尾に追加する
2. `classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff` を追加する
3. 全ノードに `class <node_ids> default` を付与する
4. 全サブグラフに `style <subgraph_name> fill:#1a1a1a,stroke:#fff,color:#fff` を付与する
5. 既存の `style`/`classDef`/`class` 行は重複しないよう整理する

### 7.4 sequenceDiagram の実装パターン
```
%%{ init: { "theme": "base", "themeVariables": {
  "background": "#000000", "mainBkg": "#000000",
  "textColor": "#ffffff", "lineColor": "#ffffff",
  "actorBkg": "#000000", "actorTextColor": "#ffffff",
  "actorLineColor": "#ffffff", "noteBkgColor": "#000000",
  "noteTextColor": "#ffffff", "noteBorderColor": "#ffffff" } } }%%
sequenceDiagram
    participant A as "参加者A"
    A->>B: メッセージ
```

**必須ルール:**
- `sequenceDiagram` の前に必ず `%%{ init: ... }%%` ヘッダーを挿入する
- `classDef` / `class` 行は `sequenceDiagram` では使用しない（非対応）
- ⚠️ **Note 背景の変数名は `noteBkgColor`（`noteBkg` ではない）。**
  `noteBkg` は Mermaid に認識されず既定の黄色（`#fff5ad`）になる

### 7.5 stateDiagram-v2
`classDef` / `class` に非対応 → **スタイル指定を付けない。**

### 7.6 検証（grep）
各ファイルで `flowchart|graph` の数 == `classDef default fill:#000` の数、
`sequenceDiagram` の数 == `%%{ init` の数。

---

## 8. コーディング規約

### 8.1 型ヒント
```python
# ❌ 誤り
def func(callback: Optional[callable] = None): ...

# ✅ 正しい
from typing import Optional, Callable
def func(callback: Optional[Callable] = None): ...
```

### 8.2 出力ファイル命名（チャンク分割）
```bash
# ✅ デフォルト: 固定ファイル名（後続バッチとの連携のため）
cc_news_1per.csv  →  output_chunked/cc_news_1per_chunks.csv

# タイムスタンプが必要な場合は --timestamp オプションで明示指定
python -m chunking.csv_text_to_chunks_text_csv \
  --input-file OUTPUT/cc_news_1per.csv \
  --output output_chunked \
  --timestamp   # ← これがある場合のみ日時サフィックスを付与
```

---

## 9. ドキュメント規約

### 9.1 所在は `docs`（複数形）に統一

| 領域 | 所在 |
|---|---|
| Python モジュール（IPO） | `<package>/docs/<module>.md` — `chunking/docs/`, `qa_generation/docs/`, `qa_qdrant/docs/`, `services/docs/`, `grace/docs/`, `grace/step_trace/docs/` |
| backend | `backend/docs/` |
| React コンポーネント | `frontend/docs/<Component>.md` |
| 横断/設計メモ | リポジトリ直下 `docs/` |

**単数形 `doc/` は使わない。** 新規ディレクトリも必ず `docs/` で切る。

### 9.2 フォーマット仕様（書く前に該当仕様を実際に読むこと）

| 対象 | 仕様書（`.claude/skills/` 配下） |
|---|---|
| Python モジュール | `grace-agent-docs/a_class_method_md_format.md`（IPO 形式） |
| React コンポーネント | `grace-agent-docs/a_react_page_md_format.md` |
| 単体テスト | `grace-agent-tests/a_test_md_format.md`（SAE 形式） |

> `grace-agent-docs/a_pages_md_format.md` は **Streamlit 用**。
> **本リポジトリに Streamlit は存在しない**（他リポジトリ用に同梱しているだけ）。

### 9.3 技術スタック表記の統一

| 用途 | ✅ 正しい表記 | ❌ 禁止表記 |
|---|---|---|
| LLM全般 | `Anthropic Claude` | `OpenAI GPT`, `Gemini`（LLM 用途） |
| デフォルトモデル | `claude-sonnet-5`（最上位 `claude-fable-5-1` / 上位 `claude-opus-5-5` / 軽量 `claude-haiku-4-5`・日付指定 `claude-haiku-4-5-20251001`） | `gpt-4o-mini`, `gemini-2.5-flash` |
| Embedding | `Gemini` `gemini-embedding-001`（3072次元） | `text-embedding-3-*`（本番 Embedding 用途） |
| LLMクライアント | `create_llm_client("anthropic")` | `"openai"` / `"gemini"`（LLM 用途） |
| LLM用APIキー | `ANTHROPIC_API_KEY` | `OPENAI_API_KEY` |
| エージェント名 | `GRACE-Support` / `GRACE-Review` | `GRACE` 単独で Support だけを指すこと |
| フロントエンド | `Vite + React 18 + TypeScript` | `Streamlit`, `Next.js` |

> `claude-haiku-4-5`（日付なし）は**実在するエイリアスでチャンキングの既定値**。
> 日付付きへ「統一」しないこと（§3.2）。
>
> `claude-sonnet-4-6` は**旧既定**。履歴・変更履歴の記述では当時の値として残す
> （現在の既定を述べる箇所だけ `claude-sonnet-5` にする）。

### 9.4 参照してはいけない廃止ファイル
grace_v2 に**存在しない**: `setup.py` / `server.py` / a-prefixed scripts
（`a30_qdrant_registration.py` 等）/ `agent_rag.py` / `ui/` /
リポジトリ直下の `tests/` / `test_celery_integration.py` /
**`agent_support_example.py`** / **`grace/step_trace/s0_arg.py`〜`s9_render.py`**
（後ろ 2 つは 2026-09-19 に削除。§1・§2 の注記を参照）。

> ⚠️ **`start_celery.sh` は存在する**（2026-09-12 訂正）。以前この一覧に
> 入っていたが、Q/A 生成の Celery 並列（CLI の `--use-celery` / データ管理タブの
> 「② Q/A 作成」）を使うときのワーカー起動口として追加した。手順は
> `qa_qdrant/docs/celery_quick_start.md`。
>
> ⚠️ **Celery のキュー名に `qa_generation` は無い。** `celery_config.py` が定義
> するのは `celery`（既定）/ `high_priority` / `normal_priority` / `low_priority`
> の 4 つで、`qa_generation` は `Celery('qa_generation')` の**アプリ名**である。
> `-Q qa_generation` で起動したワーカーは何も消費しない。`-A` に渡すのは
> `celery_config`。

---

# ⚠️ CRITICAL RULES - MUST READ BEFORE ANY MODIFICATION ⚠️

## R1. モデル名のマッピングを絶対に作らない

**以下はすべて実在する有効なモデル名:**
- `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5`, `claude-opus-5`, `claude-haiku-4-5`, `claude-haiku-4-5-20251001`, `claude-sonnet-4-6`
- `gpt-5-nano`, `gpt-5-mini`, `gpt-5` ← 実在する GPT-5 系
- `gpt-4.1`, `gpt-4.1-mini` ← 実在する GPT-4.1 系
- `o3`, `o3-mini`, `o4`, `o4-mini` ← 実在する O 系

**❌ こういうマッピングを作ってはならない:**
```python
MODEL_MAPPING = {"gpt-5-nano": "gpt-4o-mini"}  # ← WRONG! DO NOT DO THIS
```

モデル名は定義済みのものをそのまま使う。

## R2. OpenAI API のメソッドは 2 つとも正しい

```python
# Structured Outputs API（Q/A 生成向け・型安全）
response = client.responses.parse(
    input=combined_input, model=model,
    text_format=QAPairsResponse, max_output_tokens=1000,
)

# Responses API（標準のテキスト生成）
response = client.responses.create(
    input=input_messages, model=model, max_output_tokens=1000,
)
```

**⚠️ `.parse()` と `.create()` は両方 CORRECT。用途に応じて使い分ける。**
片方をもう片方へ「修正」しない。

## R3. よくある間違い

| ❌ 誤り | ✅ 事実 |
|---|---|
| 「`gpt-5-nano` はエラーになるから存在しないモデルだ」 | 実在する。**本当のエラー原因**を調べること |
| 「`responses.parse()` は存在しないから `create()` に直そう」 | 両方存在する |
| 「旧モデル名を新モデル名に翻訳するマッピングを作ってあげよう」 | モデル名は既に正しい。マッピングを作らない |

## R4. エラーが出たときの手順

「model not found」「API error」を見たら:

1. ❌ モデル名が間違っているせいでは**ない**
2. ❌ API メソッド名が間違っているせいでは**ない**
3. ✅ 確認する: API キー、ネットワーク、Qdrant 起動状態、Celery/Redis 接続
4. ✅ 確認する: 実際のエラーメッセージとスタックトレース
5. ✅ **モデル名や API メソッド名を「直す」ことを最初の対応にしない**

## R5. コミット前チェックリスト

- [ ] MODEL_MAPPING を作っていないか？（作っていたら → 削除）
- [ ] `responses.parse()` を `responses.create()` に変えていないか？（変えていたら → 戻す）
- [ ] 4 つの CI ゲート（ruff / pytest backend / compileall / frontend）をローカルで通したか？
- [ ] API スキーマを変えたなら `frontend/src/types.ts` を追随させたか？
- [ ] **grace_v2_local から移植したなら**、こちらにしかない機能（`formMemory` 等）を
      消していないか？（§5・ファイルを丸ごとコピーしていないか）
- [ ] フロントの判断ロジックをコンポーネント内に書いていないか？
      （§6・`state/` の純関数へ出さないとテストできない）
- [ ] コンポーネントを変えたなら `frontend/docs/<Component>.md` を追随させたか？
- [ ] ドキュメントに書いたテスト件数は**実行して数えた値**か？（記憶で書かない）
- [ ] **Review 側**（`review_agent.py` / `review_gates.py` / `rulesets.py` /
      `ReviewPanel` 系）を壊していないか？ 共用部品（`GroundednessVerifier` /
      `InterventionBridge` / `support_actions.py`）を触ったなら
      `backend/tests/test_review_*.py`（18 本）も通したか？（§1）
- [ ] モデル既定を変えたなら**4 本の解決経路すべて**を確認したか？（§3.1）
      新しい既定を `SELECTABLE_MODELS` と `MODEL_PRICING` / `MODEL_LIMITS` へ入れたか？
- [ ] 確信が持てない → **ユーザーに聞く**
