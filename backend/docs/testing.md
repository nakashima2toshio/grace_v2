# backend テストの地図 ドキュメント

**Version 2.7** | 最終更新: 2026-10-06

---

## 目次

- [概要](#概要)
- [1. 実行方法](#1-実行方法)
  - [1.1 結合テスト（実 Qdrant / Redis）](#11-結合テスト実-qdrant--redis)
  - [1.2 E2E（実 LLM・実 Embedding・実データ）](#12-e2e実-llm実-embedding実データ)
- [2. テストの地図](#2-テストの地図)
- [3. どこを触ったらどれを流すか](#3-どこを触ったらどれを流すか)
- [4. 設計方針](#4-設計方針)
- [5. CI の 4 ゲート](#5-ci-の-4-ゲート)
- [6. 変更履歴](#6-変更履歴)

---

## 概要

> **本書の位置づけ**: `backend/tests` に何があり、**どこを触ったらどれを流すか**をまとめる。
> テストの書式（SAE 形式）は `.claude/skills/grace-agent-tests/a_test_md_format.md`、
> CI の設定は `.github/workflows/ci.yml` が正本。

> **関連ドキュメント**
> - [`architecture.md`](./architecture.md) — どのモジュールが何を担うか
> - [`pitfalls.md`](./pitfalls.md) — 共用部品を壊さないための注意
> - [`install_and_setup.md`](./install_and_setup.md) — 実行環境の準備

### 結論

- 実行は `uv run --no-sync pytest backend/tests -q -rs`（§1）。実 API キー・Qdrant は不要
- **例外は `backend/tests/integration/`（§1.1）**。実 Qdrant / Redis に接続し、未起動なら skip する。クラウド VM では SessionStart hook が両方を起動するので走る
- **E2E は `backend/tests/e2e/`（§1.2）**。実 API を呼んで課金されるので `GRACE_E2E=1` のときだけ走る。実データは Mac の Qdrant からスナップショットで VM へ運ぶ（`scripts/qdrant_snapshot.py`）
- **どこを触ったらどれを流すか**は §3。共有基盤（`jobs.py` ほか）と共用部品を触ったら全体を流す
- CI の必須ゲートは 4 つ（§5）

### 対象モジュール

| # | モジュール | 関係 |
|---|---|---|
| 1 | `backend/tests/` | テスト本体（§2 の地図） |
| 2 | `requirements-test.txt` | テスト用依存の正本（CI と共有） |
| 3 | `.github/workflows/ci.yml` | 4 ゲートの定義 |
| 4 | `backend/tests/integration/` | 結合テスト（§1.1） |
| 5 | `.claude/hooks/session-start.sh` | クラウド VM でテスト依存を入れ、Qdrant / Redis を起動する。`GRACE_E2E_SNAPSHOT_URL` があれば実データも復元する |
| 6 | `backend/tests/e2e/` / `requirements-e2e.txt` | E2E（§1.2）とその追加依存 |
| 7 | `scripts/qdrant_snapshot.py` | E2E 用の実データを Qdrant スナップショットで書き出す / 復元する（§1.2） |

---

## 1. 実行方法

**実 API キー・実 Qdrant は不要**（外部依存は `conftest.py` がスタブへ差し替える）。

> ⚠️ **キーが「無くてよい」だけでなく、「あっても結果が変わらない」ことを保つ。**
> `RAGSearchTool.execute` は候補コレクションが 2 つ以上あると `_embed_query_once` で
> クエリを実 Embedding API（Gemini）に 1 回だけ埋め込み、検索関数へ `precomputed_*` を渡す。
> キーが無い環境（CI）では埋め込みが失敗して `None` になるため表に出ないが、
> `GOOGLE_API_KEY` がある環境では**単体テストから実 API を呼び**、`lambda _q, col: ...` の
> ような 2 引数スタブが例外になって 0 件になる（2026-09-26 に 8 件の失敗として実測）。
> **`execute` を回すテストは `_embed_query_once` を `(None, None)` に差し替える**
> （`test_rag_adoption.py` / `test_memory_exclusion.py` / `test_collection_selection.py` の補助関数）。
> 埋め込みの再利用そのものは `test_query_vector_reuse.py` が `embed_query` を差し替えて検証している。

```bash
# 初回のみ: テスト用の依存（CI と共有する唯一の正本）
uv venv
uv pip install -r requirements-test.txt

# 実行
uv run --no-sync pytest backend/tests -q -rs
```

> ⚠️ **`--no-sync` を付ける。** 付けないと `uv run` が `pyproject.toml` の
> `[project] dependencies`（221 行・spacy / matplotlib 等）で環境を同期し直し、
> `requirements-test.txt` で作った軽い環境が上書きされる。

> ⚠️ **`backend/tests` が import するパッケージを足したら `requirements-test.txt` に追記する。**
> CI はこのファイルを読むので、YAML 側を直す必要は無い。

**実測（2026-09-16）**: `978 passed, 1 skipped, 3 warnings in 9.51s`。
スキップ 1 件は `test_config_file_and_memory.py`（`logs/` が無い環境では対象外）。

### 1.1 結合テスト（実 Qdrant / Redis）

`backend/tests/integration/` だけは**スタブを使わず**、`docker-compose/docker-compose.yml` の
Qdrant（:6333）と Redis（:6379）に実際に接続する。API キーは使わない
（Embedding は固定ベクトル、LLM は固定応答の生成器へ差し替える）。

| 状況 | 挙動 |
|---|---|
| Qdrant / Redis が起動している | 走る（18 件・約 5 秒） |
| 起動していない（CI・Docker を止めた Mac） | **skip**（理由に起動コマンドを出す） |
| `GRACE_SKIP_INTEGRATION=1` | 起動していても skip |
| `-m "not integration"` | 収集から外す（`deselected`） |

```bash
# Mac: Docker Desktop で起動してから
docker compose -f docker-compose/docker-compose.yml up -d
uv run --no-sync pytest backend/tests/integration -q -rs

# クラウド VM（Claude Code on the web）: セッション開始時に
# .claude/hooks/session-start.sh が dockerd と compose を起動済み。そのまま流す
```

> ⚠️ **共用 Qdrant（grace_v2_local と同じもの）を壊さない。** 作るコレクションは
> `grace_it_<乱数>` だけで、テストごとに削除する。既存コレクションには触れない。
> Redis は **db 15** を使う（Celery の既定は db 0）。Mac で常駐している本物のワーカーに
> テストのタスクを拾わせないためで、Celery アプリのキャッシュ済み接続を捨てて
> **db 15 を向いたことを assert してから**投入する。

| テスト | 見ていること（スタブでは分からない点） |
|---|---|
| `test_qdrant_live.py`（12 件） | `create_or_recreate_collection` の設定（sparse・`domain` 索引・recreate）、`stable_point_id` による再登録の冪等性、`search_collection` の経路選択（dense / sparse 未設定なら hybrid を投げない / hybrid で sparse が順位を変える / 無いコレクションは `[]`）、`get_all_collections` / `QdrantDataFetcher` |
| `test_register_to_qdrant_live.py`（4 件） | `register_to_qdrant` の CSV → Qdrant 登録（重複行は **Embedding 前に**落とす・Embedding メタデータ・ファイル名の日時サフィックス除去・再登録の冪等性・batch_size=1 の先読みパイプライン・登録ベクトルで自分が 1 位） |
| `test_qdrant_snapshot_live.py`（7 件） | `scripts/qdrant_snapshot.py` の export → restore 往復（点数・ペイロードの再現、HTTP 経由、既存を上書きしない / `--force`、Embedding モデル違いと sha256 不一致の拒否、Qdrant にスナップショットを残さない） |
| `test_celery_redis_live.py`（2 件） | テスト内で本物の Celery ワーカー（solo）を立て、`submit_unified_qa_generation` → Redis → タスク → Redis → `collect_results` を往復（JSON を経た戻り値の形・usage 合算・空チャンク・完了通知・result backend への保存） |

**実効性の確認（2026-10-03）**: 本番コードを次のように壊すと、それぞれ落ちることを確かめた。

| 壊し方 | 落ちたテスト |
|---|---|
| `stable_point_id` を乱数にする | `test_upsert_twice_does_not_duplicate` / `test_reregistering_without_recreate_is_idempotent` |
| `_get_vector_config` の `has_sparse` を常に False | `test_hybrid_search_lets_sparse_change_ranking` |
| `register_to_qdrant` の重複テキスト除去を外す | `test_registers_unique_rows_with_embedding_metadata`（※ 件数だけでは検出できない。内容ベース ID で同じ点に上書きされるため。Embedding に渡った件数で見る） |
| ワーカーの usage を捨てる | `test_qa_generation_roundtrip_through_redis` |
| restore の「既存を上書きしない」/ モデル照合 / sha256 照合を外す | それぞれ `test_existing_collection_is_not_overwritten_without_force` / `test_refuses_snapshot_from_another_embedding_model` / `test_refuses_tampered_snapshot` |
| tar の名前チェックを外す | `test_qdrant_snapshot.py::TestSafeExtract::test_rejects_unexpected_members`（4 件） |

> 📝 Celery のテストは本番の `rate_limit`（`generate_qa_for_chunk` は 60/m）を**テスト中だけ**外す。
> 効いたままだと solo ワーカーで 3 タスクに約 10 秒かかる（実測）。終了時に元へ戻す。

**実測（2026-10-03・クラウド VM・サービス起動中）**: `1342 passed, 7 skipped`（うち結合 25 件。skip は
`logs/` の 1 件と E2E の 6 件）。サービス停止中は `1317 passed, 32 skipped`（結合 25 件も skip）。

### 1.2 E2E（実 LLM・実 Embedding・実データ）

`backend/tests/e2e/` は、**本物の API と実データ**で `run_support_agent_core` /
`run_review_agent_core` を丸ごと流す。スタブを一切使わない。**課金される**ので
`GRACE_E2E=1` を付けたときだけ走り、それ以外（CI を含む）は skip する。

| ケース | 入力（画面の例文ボタンから読む） | 期待 |
|---|---|---|
| Support / gov | 住民票の写しの取り方は？ | `answer`・社内ナレッジの出典あり・根拠検証で判定できた主張 > 0・情報なし検知なし・回答に「300円」 |
| Support / saas | サービスが落ちています | エスカレーション語「落ち」で強制エスカレ → `escalate_to_human`。Web の出典が混ざらない・回答に「status.example.jp」 |
| Support / ec | 返品したい | アクションあり・社内ナレッジの出典あり・判定とアクションが一致（answer → `create_ticket` / escalate → `escalate_to_human`）・本人確認を通る・回答に「14日」 |
| Support / gov（範囲外） | 明日の東京の天気を教えてください（**画面に無い**） | `escalate`（社内ナレッジに無い答えをでっち上げない） |
| Review / 化粧品LP案 | NG 例（優良誤認・薬機法） | 指摘 ≥ 1・high ≥ 1（記録のみ: `keihyo-03` / `keihyo-04` / `yakki-02` / `yakki-04`） |
| Review / 表記漏れLP案 | NG 例（表記漏れ） | `tokusho-01`（送料の欠落）が出る（記録のみ: `policy-01`） |
| Review / 適正LP案 | OK 例 | **指摘 0 件**（過検知の回帰） |

- **文面は書き写さない。** `cases.py` が `QueryForm.tsx` / `ReviewForm.tsx` の例文を読む。
  例文が増えたり名前が変わったりして期待値とずれると、`test_e2e_cases.py`（API を呼ばないので CI で走る）が落ちる。
- アクションは必ず**ドライラン**。Web 検索は既定で使わない（`GRACE_E2E_USE_WEB=1` で使う）。
  Support の各テストは、このとき **Web を検索していない（`used_web=False`）・Web の出典が無い**ことも確かめる。
  ⚠️ 2026-10-04 の初回実行（Mac）までは、`use_web=False` が止めていたのは ⑤ Web フォールバックだけで、
  executor は RAG スコア不足時に自分で Web を検索していた（saas で無関係な URL が出典に 9 件）。
  §1.2 初版のこの一文は当時は誤りだった。同日に executor の全経路で止めるよう直した（`support_flow.md` v3.4）
- **回答の事実チェック**（`cases.SUPPORT_FACTS`）: 判定と出典だけだと、出典を付けたまま中身の薄い回答
  （「担当窓口へお問い合わせください」だけ等）を見逃す。社内ナレッジにある具体値（数値・固有名）が回答に入っているかを見る。
  全角/半角・空白・桁区切りの違いは無視する（`contains_fact`）。値は Mac の実測 2 回で 2 回とも回答に入っていたもの。
- **範囲外の質問**（`cases.OUT_OF_SCOPE`）: 画面の例文は「答えがある」質問だけなので、答えが無い質問で
  でっち上げないことを 1 件だけ見る。
- **記録だけの期待値**（`cases.REVIEW_WATCH`）: Review の指摘は ③ Detect（LLM）に依るので、1 回で fail にすると揺れで赤くなる。
  出なかったものはレポートの `missing_expected` に残し、下の繰り返し実行で出現率を見る。
- 結果（回答・出典・判定・指摘・所要時間・sparse の有無・**実際のモデル名**・合否）は `logs/e2e/e2e_<日時>.json` に書き出す。
  **合否だけでなく回答の中身を人が読む**ためのもの。形は `{"repeat": N, "summary": {ケース: 集計}, "records": [1 回ごとの結果]}`。
- **揺れの計測**（`GRACE_E2E_REPEAT=N`）: 各ケースを N 回流し、`summary` にケースごとの合格率（`pass_rate`）・
  指摘の出現率（`rule_id_rate`）・事実や期待した指摘が欠けた率（`missing_rate`）・平均所要時間・失敗理由を出す。
  `record` まで届かずに例外で落ちた回も失敗 1 回として数える。課金は N 倍（まず 3 程度で）。

> ⚠️ **API が失敗してもパイプラインは例外を出さず、安全側の結果を返す**（Support はエスカレ、
> Review は全ルールを「自動判定に失敗したため要確認」で残す）。そのため素朴な期待値だと
> **キーが無効でも合格する**（2026-10-03 にダミーキーで実測: 6 件中 4 件が passed）。対策は 2 段:
>
> 1. `e2e_ready` が最初に Anthropic（`models.list`・課金なし）と Gemini Embedding を 1 回ずつ呼ぶ。
>    失敗したら全件 ERROR（実測: 6 errors・理由「Anthropic API を呼べない」）
> 2. `api_errors` が実行中の API エラーのログ（`Error code: 4xx/5xx`・`INVALID_ARGUMENT`・
>    `RAGツールエラー` など）を拾い、各テストは 1 件でもあれば fail。Review は「自動判定に失敗」の
>    指摘も fail にする（実測: 1 を外しても 6 failed）

**初回の実測（2026-10-04・Mac・実データ各 10 点前後）**: `6 passed`（87 秒）。回答・指摘の中身も
妥当だった（gov は `gov_faq.csv` を出典に groundedness 1.00、表記漏れLP案は 4 件、適正LP案は 0 件）。
ただし saas の出典に無関係な Web の URL が 9 件混ざっており、これが上の `use_web` の不具合の発見につながった。

**修正後の実測（2026-10-04・Mac）**: `6 passed`（80 秒）。saas の出典は `[社内] saas_docs.csv` だけになり、
Support 3 件とも `used_web=false`。Web を検索しなくなった分だけ短くなった。

**2026-10-05 の実測（Mac）**: 7 件（範囲外の質問を追加）すべて passed。grace_v2 は 81 秒、grace_v2_local は 718 秒。
事実チェック（`missing_facts`）・記録だけの期待値（`missing_expected`）とも欠けなし。範囲外の質問（天気）は
回答を作らずに `escalate`（社内ナレッジに該当なし）。同日の `scripts/measure_rag_scores.py`（現在は `scripts/measure_rag_threshold.py` に統合）の結果は
`config/grace_config.yml` の `reasoning_min_rag_score` のコメントに残した（しきい値 0.64 は据え置き）。

- レポートの `model` / `light_model` は**実際に使ったモデル名**を記録する（以前は `(config llm.model)` としか残らず、
  モデルを替えた結果を比べられなかった）。
- 事前確認（`_preflight`）は `GRACE_E2E=1` とキーが揃ったときしか動かないので、`test_e2e_preflight.py`
  （API を呼ばないので CI で走る）がスタブで通しておく。grace_v2_local では事前確認が存在しない設定値を読み、
  Mac で 6 件すべてが ERROR になった（2026-10-04）。Embedding の次元違いを「キーが無効」と表示しないよう判定も分けた。

#### 走らせ方

```bash
# Mac（.env にキー・Qdrant に実データ・E2E 用の追加依存）
uv pip install -r requirements-e2e.txt
GRACE_E2E=1 uv run --no-sync pytest backend/tests/e2e -m e2e -rs
GRACE_E2E=1 GRACE_E2E_REPEAT=3 uv run --no-sync pytest backend/tests/e2e -m e2e -rs   # 揺れを測る（課金 3 倍）

# クラウド VM: 下の準備をしたうえで新しいセッションを開くと、hook が依存と実データを用意する
GRACE_E2E=1 uv run --no-sync pytest backend/tests/e2e -m e2e -rs
```

#### クラウド VM で走らせる準備（初回だけ）

1. **Mac で実データを書き出す**（アプリが検索するコレクションを `verticals.py` / `rulesets.py` から集める）:
   ```bash
   python scripts/qdrant_snapshot.py list     # 何があるか
   python scripts/qdrant_snapshot.py export   # → grace_e2e_snapshot.tar.gz（.gitignore 済み）
   ```
2. **非公開の保存先に置き、署名付き URL を発行する。** ⚠️ **GitHub には置かない**
   （本リポジトリは public。`gov_faq.csv` などの元データはリポジトリに入っていない）。
   VM の既定のネットワーク設定から届くことを確認した保存先（2026-10-04 実測）:

   | 保存先 | VM から | 署名付き URL の作り方（例） |
   |---|---|---|
   | Google Cloud Storage | ✅ `storage.googleapis.com` | `gcloud storage cp grace_e2e_snapshot.tar.gz gs://<バケット>/` → `gcloud storage sign-url gs://<バケット>/grace_e2e_snapshot.tar.gz --duration=7d --impersonate-service-account=<SA>`（V4 署名は最長 7 日。サービスアカウントが要る） |
   | Amazon S3 | ✅ `s3.amazonaws.com` | `aws s3 cp grace_e2e_snapshot.tar.gz s3://<バケット>/` → `aws s3 presign s3://<バケット>/grace_e2e_snapshot.tar.gz --expires-in 604800`（最長 7 日） |
   | Google ドライブ / Dropbox | ❌ 届かない（`drive.google.com` / `dl.dropboxusercontent.com` が拒否される） | — |

   ⚠️ 署名付き URL には**期限がある**。切れると hook のサマリが `e2e-data:FAILED` になり、
   ログ（`/tmp/grace-session-start/restore.log`）に「期限切れの可能性」と出るので発行し直す。
3. **クラウド環境の設定**（セッション画面のクラウド環境メニュー → Edit）で環境変数を追加する:
   `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `GRACE_E2E_SNAPSHOT_URL`。
   キーは E2E 専用の、上限額を低くしたものを推奨。
4. 新しいセッションを開く。hook のサマリに `e2e-data:N restored` と出れば準備完了。

**VM での通し確認（2026-10-04）**: 保存先の代わりに VM 内の HTTP サーバから署名付き URL 風の URL
（`...?X-Goog-Signature=...`）で配り、hook を流した。

| 状況 | hook のサマリ |
|---|---|
| 初回（コレクション無し） | `e2e-data:2 restored,0 skipped`（点も復元された） |
| 同じコンテナで再開 | `e2e-data:restored(earlier)`（ダウンロードし直さない） |
| URL が無効（404） | `e2e-data:FAILED(...)`、ログに「ダウンロードに失敗しました（HTTP 404）。署名付き URL なら期限切れの可能性」 |
| キー未設定 | `e2e:ANTHROPIC_API_KEY-missing e2e:GOOGLE_API_KEY-missing`（E2E は理由つきで skip） |

`storage.googleapis.com` へは、VM の httpx（エージェントプロキシ経由）で公開オブジェクトを
取得できることも確かめた（206）。**実際の保存先・実キーでの通しはまだ**（キーと保存先は利用者の設定が要る）。

> ⚠️ **既定のネットワーク設定では `huggingface.co` と `duckduckgo.com` に届かない**（2026-10-03 実測）。
> - `huggingface.co`（と `cdn-lfs.huggingface.co`）: hybrid 検索の sparse モデル（SPLADE）を取得できず、
>   **dense だけで検索する**（アプリはそう倒れる作り）。Mac と結果を揃えたいなら、環境の設定の
>   Network access を Custom にして `huggingface.co` と、モデル本体の配信元（`cdn-lfs.huggingface.co` / `*.hf.co`）を
>   Allowed domains に足す（パッケージマネージャの既定リストは残す）。
>   fastembed 0.7.4 の `prithivida/Splade_PP_en_v1` は Hugging Face（`Qdrant/Splade_PP_en_v1`）からしか取得しない
>   （GCS のミラーは無い）。使えたかどうかはレポートの `sparse` に残る
> - `duckduckgo.com` ほか: Web 検索が失敗する。E2E は既定で Web を使わないので影響しない
>
> `restore` は**点が入っている既存コレクションを上書きしない**（`--force` で上書き）。
> Embedding モデルが違うスナップショットは拒否する（CLAUDE.md §3: エラーにならず検索結果だけが壊れるため）。

---

## 2. テストの地図

実測 2026-09-16: `test_*.py` が **58 ファイル**、`def test_` が **867 個**
（パラメータ化を展開した実行数が上の 978）。

### 2.1 GRACE-Review 系（18 ファイル）

**`backend/tests` の約 1/3 が Review 系**である。共用部品を触ったら必ず流す。

| テスト | 対象 |
|---|---|
| `test_review_agent_core.py` | パイプライン S1・①〜⑦ の配線と KPI カウンタ |
| `test_review_gates.py` | しきい値による status 判定・救済・severity 調整・強制 high |
| `test_review_api.py` | submit / stream / confirm / result の応答、422 ガード |
| `test_rulesets.py` | `RuleSet` / `RuleItem` の整合（`always_check` と `keywords` の排他ほか） |
| `test_review_evidence_threshold.py` / `test_review_evidence_top_ratio.py` | ② Retrieve の根拠採用しきい値 |
| `test_review_rule_query_retrieve.py` | ② Retrieve をセグメント本文ではなくルール自身で検索する（条文が ③④ に届く・別ルールの行を根拠にしない・ルールごとに 1 回） |
| `test_review_cosmetic_lp_expected.py` | 画面のサンプル「化粧品LP案」の期待値（確実な 5 件が判定に回り残る・強制 high 3 件）、keihyo-07 を確定にしない、keihyo-08 の判定基準、修正案と文面の指示 |
| `test_review_document_context.py` | 段落単位の ③ Detect に文書の文脈（題名＋冒頭）を渡す（yakki-01 が商品の種類を判断できる）・文書全体のルールには渡さない・tokusho-01 の税込表記の判定基準 |
| `test_review_keyword_excludes.py` | 第1段の候補検出で `keyword_excludes` の一部としてだけ現れた keyword を数えない（keihyo-09 が「期間限定」に反応しない・数量限定は引き続き拾う） |
| `test_review_facts.py` | 文字列で決まる事実（`review_facts`）: 購入時の送料の有無（返品の行は数えない）・返品条件の比較（期限・条件語・返送料）と、③ の取りこぼし補完／④' の抑止の配線 |
| `test_review_document_scope.py` / `test_review_document_excerpt.py` / `test_review_absence_excerpt.py` | 文書全体スコープ（`always_check`）の扱い |
| `test_review_detect_criteria_in_prompt.py` / `test_review_detect_failure_status.py` | ③ Detect のプロンプトと判定失敗時の安全側 |
| `test_review_ground_sources.py` / `test_review_undecided_groundedness.py` | ④ Ground の出典と「判定できていない」の扱い |
| `test_review_rule_subject_scope.py` / `test_review_multi_item_rules.py` / `test_review_no_duplicate_findings.py` | ルール主題の限定・重複指摘の抑止 |
| `test_review_policy_evidence.py` / `test_review_safety_claim.py` / `test_review_yakki_product_scope.py` | 個別ルールの回帰 |
| `test_export_ruleset_to_csv.py` | ルールセットの書き出し |

> 📝 **設計時の想定と実装は一致していない。** 旧 `review_spec.md` §9 は
> `test_review_segment.py` を挙げていたが、そのファイルは**存在しない**（実測 2026-09-16）。
> ① Segment の検証は `test_review_agent_core.py`（`split_segments` を直接呼ぶ）にある。

**過検知の回帰テスト**を重視している（`backend/tests/data/` の 3 サンプル）。

| サンプル | 期待 |
|---|---|
| `ec_ad_ng_sample.txt` | 意図的に違反を仕込んだ LP（各カテゴリ 1 件以上） |
| `ec_ad_ok_sample.txt` | 適正表記の LP → **指摘 0 件**（過検知テスト） |
| `ec_ad_edge_sample.txt` | 否定文脈の「No.1」等 → **強制 high にしない**（誤検知抑止テスト） |

### 2.2 GRACE-Support 系

| テスト | 対象 |
|---|---|
| `test_support_agent_core.py` | パイプライン 0-(A)〜⑥ の配線（14 件） |
| `test_multi_question.py` / `test_multi_question_pipeline.py` | 0-(A) 複数質問の分析・選択・再構成（85 件） |
| `test_no_info_judge.py` / `test_no_info_prediction.py` | ④' 情報なし回答検知 |
| `test_vertical_scope.py` | 業界プロファイルによる検索スコープ限定 |
| `test_policy_claims.py` / `test_source_attribution.py` / `test_rag_adoption.py` | 出典・根拠の扱い |
| `test_web_search_toggle.py` | `use_web=False`（内部 RAG のみ）で executor の 5 経路（動的挿入・計画済み・並列プリフェッチ・fallback・ReAct）すべてが Web を検索しない。`ask_user` も差し込まない。Web 許可時も、採用した RAG 結果（0.64 以上）では無条件に Web を検索しない（`rag_sufficient_score` ≤ `reasoning_min_rag_score` の不変条件） |
| `test_uncited_web_citations.py` | 回答本文で引用していない Web 出典を表示から外す（社内だけ引用 → Web を外す／URL を引用 → それだけ残す／どちらも引用なし → 外さない） |

### 2.3 共有基盤・API・データ準備

| テスト | 対象 |
|---|---|
| `test_jobs_generic.py` | **ジョブ基盤の汎用化（Support の既存挙動が変わらないことの回帰・18 件）** |
| `test_intervention_bridge.py` | HITL 承認の橋渡し（タイムアウト＝実行しない） |
| `test_job_logs.py` | ログ転送（スレッド絞り込み・level の参照カウント） |
| `test_done_event_timing.py` | `done` 番兵の `ts` / `started_at` |
| `test_api.py` | Support API の応答 |
| `test_data_jobs.py` / `test_data_pipeline.py` / `test_chunking_abort.py` / `test_collection_selection.py` | データ準備 4 ジョブ |
| `test_config_isolation.py` / `test_config_file_and_memory.py` / `test_scope_and_models.py` / `test_model_table_coverage.py` | 設定・モデル解決 |
| `test_celery_worker_init.py` | Celery ワーカー起動時の初期化（`configure_worker_process`）が ERROR を出さず、タスクが実際に使う `qa_generation.smart_qa_generator` を確かめる（削除済みの `qa_generation.generation` を見ていた回帰） |
| `integration/test_*_live.py`（4 ファイル） | **実 Qdrant / Redis の結合テスト**（§1.1。未起動なら skip） |
| `test_qdrant_snapshot.py` | `scripts/qdrant_snapshot.py` の Qdrant を使わない部分（対象コレクションの集め方・tar の検査・CLI） |
| `test_measure_rag_threshold.py` / `integration/test_measure_rag_threshold_live.py` | `scripts/measure_rag_threshold.py`（RAG のしきい値の実測・LLM 不使用）の判定（分離可否・推奨値・今のしきい値での帯。**他業界の質問は判定に混ぜず参考として別に数える**）と業界ごとの集計・質問の組み立て／実 Qdrant で全コレクション中の最良スコアを拾えるか。grace_v2_local と同じ内容 |
| `e2e/test_*_e2e.py`（2 ファイル） / `e2e/test_e2e_cases.py` / `e2e/test_e2e_preflight.py` | **E2E**（§1.2。`GRACE_E2E=1` のときだけ）／ そのケース定義・事前確認（CI で走る） |

---

## 3. どこを触ったらどれを流すか

| 触った場所 | 最低限流すもの |
|---|---|
| `core/jobs.py` / `intervention_bridge.py` / `job_logs.py`（**共有基盤**） | 全体（`pytest backend/tests`）。特に `test_jobs_generic.py` |
| `core/gates.py`（Support の判定） | `test_support_agent_core.py` `test_multi_question*.py` `test_no_info_*.py` ＋ **Review 系 18 本**（`_match_keyword` / `judge_model` を共用） |
| `core/review_*.py` / `rulesets.py` | `test_review_*.py` `test_rulesets.py` |
| `grace.confidence` / `support_actions.py`（**Support / Review 共用**） | 全体 |
| `schemas.py` / `api/*.py` | `test_api.py` `test_review_api.py` ＋ **frontend ゲート**（`types.ts` の追随） |
| `core/data_jobs.py` | `test_data_jobs.py` `test_data_pipeline.py` |
| `qdrant_client_wrapper.py` / `services/qdrant_service.py` / `qa_qdrant/register_to_qdrant.py` / `celery_*.py` | 上の単体テストに加えて `backend/tests/integration/`（Qdrant / Redis を起動して。§1.1） |
| 判定・閾値・プロンプト・モデル既定（`gates.py` / `review_gates.py` / `rulesets.py` / `config/grace_config.yml`） | 単体テストに加えて、できれば E2E（§1.2）。とくに「適正LP案 → 0 件」 |
| `frontend/src/components/QueryForm.tsx` / `ReviewForm.tsx` の例文 | `e2e/test_e2e_cases.py`（期待値とずれていないか） |

---

## 4. 設計方針

1. **外部依存はスタブで差し替える。** `conftest.py` が planner / executor / verifier /
   tools / LLM 分類器を置き換えるため、API キー・Qdrant・実 LLM なしで
   「イベント・HITL・判定の流れ（配線）」を検証できる。
   **Qdrant / Redis との実際のやり取り**だけは `integration/` が実物で確かめる（§1.1）。
2. **判定は純関数として固定する。** `gates.py` / `review_gates.py` の純関数は
   スタブなしで直接テストできる。判断ロジックをコアへ埋め込まない理由でもある。
3. **回帰は「修正前のコードで fail すること」を確認してから入れる。**
   fail しないテストは回帰を捕まえていない（`CLAUDE.md` 作業原則）。
4. **過検知（false positive）を最優先で固定する。** Review では「指摘が多すぎて
   読まれない」が実用上の失敗であり、`ec_ad_ok_sample.txt` が 0 件であることを守る。

> フロントエンドは `vitest`（`frontend/src/**/*.test.ts`）。**`.test.tsx` は収集されない**ため、
> 判断ロジックは `frontend/src/state/` の純関数へ出す（`CLAUDE.md` §6）。

---

## 5. CI の 4 ゲート

すべて blocking。4 つ緑になると `claude/*` ブランチの PR は auto-merge が Ready 化して master へマージする。

| ジョブ | 内容 |
|---|---|
| `compile (syntax gate)` | `python -m compileall` |
| `ruff` | `ruff check .`（`ruff==0.12.11` 固定。再現は `uvx ruff@0.12.11 check . --no-cache`） |
| `pytest (backend)` | `pytest backend/tests -q -rs`（CI に Qdrant / Redis は無いので `integration/` は skip） |
| `frontend (tsc + vitest + build)` | `npm run lint` → `npm test` → `npm run build` |

> ⚠️ **frontend ゲートを忘れない。** Python 側が全部緑でも `frontend/src/types.ts` の
> 型エラー 1 個でマージは止まる。

---

## 6. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-16 | 新規作成。`review_spec.md` §9（テスト方針）を取り込み、`backend/tests` の実測（58 ファイル / 867 関数 / 978 passed・1 skipped）から地図を書き起こした |
| 1.1 | 2026-09-24 | `a_cross_doc_md_format.md` v1.1（種別 B）に準拠（2026-09-24）。概要（結論・対象モジュール）を追加し、冒頭の説明文を概要へ移した。本文の章番号は変えていない |
| 2.7 | 2026-10-06 | 計測スクリプトの判定で、他業界の質問を範囲外（無関係）から分けたのに追随（混ぜると別の業界にも答えがある質問で「分離できない」と誤判定した） |
| 2.6 | 2026-10-05 | 計測スクリプトを grace_v2_local の `scripts/measure_rag_threshold.py` に一本化（`measure_rag_scores.py` とそのテストを統合して削除）。地図の行を差し替え |
| 2.5 | 2026-10-05 | §1.2 に 7 件での実測（grace_v2 81 秒・grace_v2_local 718 秒・全件 passed）を記録 |
| 2.4 | 2026-10-04 | 地図に `test_measure_rag_scores.py`（と結合テスト）を追加。`test_web_search_toggle.py` に Web 許可時のしきい値（`rag_sufficient_score` を 0.7 → 0.64）のテストを追記 |
| 2.3 | 2026-10-04 | §1.2 E2E の網羅性: Support の回答に社内ナレッジの事実が入っているか（`SUPPORT_FACTS`）、範囲外の質問でエスカレするか（`OUT_OF_SCOPE`）、Review の記録だけの期待値（`REVIEW_WATCH`）、`GRACE_E2E_REPEAT` による揺れの計測（合格率・出現率）を追加。レポートを `{repeat, summary, records}` の形にした |
| 2.2 | 2026-10-04 | §1.2 クラウド VM の準備に、VM から届く保存先（GCS / S3。Google ドライブ・Dropbox は不可）と署名付き URL の作り方、hook の通し確認（初回・再開・404・キー未設定）、sparse モデルの取得元と許可ドメインを追記 |
| 2.1 | 2026-10-04 | §1.2 に修正後の実測（6 passed・80 秒・saas は社内の出典のみ）を記録。E2E レポートに実際のモデル名（`model` / `light_model`）を残すようにし、事前確認を CI で通す `test_e2e_preflight.py` を追加 |
| 2.0 | 2026-10-04 | E2E の初回実測（Mac・6 passed）を記録。`use_web=False` で executor が Web を検索していた不具合（§1.2 の注記）を直したのに合わせ、Support の E2E に「Web を検索していない・Web の出典が無い」確認を追加。地図に `test_web_search_toggle.py` / `test_uncited_web_citations.py` を追加 |
| 1.9 | 2026-10-03 | §1.2 E2E（`backend/tests/e2e/`・`GRACE_E2E=1`・画面の例文を実データで流す）と、実データを VM へ運ぶ `scripts/qdrant_snapshot.py` を追加。API 失敗時に安全側の結果で合格してしまう問題への 2 段の対策を記載。結合テストを 25 件に更新 |
| 1.8 | 2026-10-03 | テストの地図に `test_celery_worker_init.py` を追加 |
| 1.7 | 2026-10-03 | §1.1 結合テスト（`backend/tests/integration/`・実 Qdrant / Redis・未起動なら skip）を追加。地図・§3・§4・§5 に反映。クラウド VM では SessionStart hook が両サービスを起動する |
| 1.6 | 2026-10-03 | テストの地図に `test_review_facts.py` を追加。スタブの `purchase_shipping_shown`（既定 True・None で実物）を conftest に追加 |
| 1.5 | 2026-10-03 | テストの地図に `test_review_keyword_excludes.py` を追加 |
| 1.4 | 2026-10-02 | テストの地図に `test_review_document_context.py` を追加 |
| 1.3 | 2026-10-02 | テストの地図に `test_review_cosmetic_lp_expected.py` を追加（化粧品LP案の期待値・確定の上限・判定基準と修正案の指示） |
| 1.2 | 2026-09-26 | §1 に「`GOOGLE_API_KEY` があっても結果が変わらないこと」の注意を追記。`RAGSearchTool.execute` を回す 3 ファイルがキーのある環境で実 Embedding API を呼び、8 件落ちていたのを是正したのに合わせた |
