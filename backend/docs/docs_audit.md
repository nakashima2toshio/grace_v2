# backend/docs 棚卸し・監査記録 ドキュメント

**Version 1.16** | 最終更新: 2026-09-26

> ⚠️ **本書は「監査記録」であって入口ではない。** 文書の地図と読む順路は
> [`README.md`](./README.md) にある。ここには実装追随の照合結果・過去に見つかった
> 記述誤り・検証スクリプト・残タスクを残す。
>
> **2026-09-16 の再編**: モジュール文書 17 本を `reference/` へ移し、横断文書
> （`architecture.md` / `job_runtime.md` / `api_contract.md` /
> `config_and_providers.md` / `pitfalls.md`）を新設した。以降の再編計画は
> [`migration_plan.md`](./migration_plan.md)。
>
> **2026-09-16 の再編 Phase 2**: `support_spec.md` を `support_flow.md` v3.0 へ、
> `review_spec.md` を `review_flow.md` v2.0 へ統合し、`verticals_and_rulesets.md` と
> `testing.md` を新設した。本書の §2 の文書一覧は**再編前の構成のまま**なので、
> **現在の構成は [`README.md`](./README.md) を見ること。**
>
> **2026-09-16 の再編 Phase 3**: `reference/` の 17 文書へ位置づけヘッダーを追加した。
> 計画していた「圧縮」は、実測（逐語重複 0〜1%・AST シンボル網羅 223/223）の結果
> **前提が成り立たないため行っていない**（[`migration_plan.md` §4](./migration_plan.md)）。

`backend/`（FastAPI + パイプライン中核）のドキュメント一覧と、実装への追随状況・
欠落・残タスク・検証手順をまとめる。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-5`（軽量 `claude-haiku-4-5-20251001`）で
> `ANTHROPIC_API_KEY` が**必須**、Embedding のみ Gemini `gemini-embedding-2`（3072 次元・`GOOGLE_API_KEY`）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で LLM 用の API キーが不要。**表記が逆**なので、
> あちらの文書をそのまま持ち込まない（CLAUDE.md §3・§5）。

> **関連**: `grace/` 側の棚卸しは [`grace/docs/README.md`](../../grace/docs/README.md)。

---

## 目次

- [1. 現在わかっている問題](#1-現在わかっている問題)
- [2. 文書一覧](#2-文書一覧)
- [3. 実装カバレッジ](#3-実装カバレッジ)
- [4. 実装追随状況](#4-実装追随状況)
- [5. 検証手順](#5-検証手順)
- [6. 残タスク](#6-残タスク)
- [7. 凡例と grep の落とし穴](#7-凡例と-grep-の落とし穴)
- [8. 変更履歴](#8-変更履歴)

---

## 1. 現在わかっている問題

| # | 問題 | 状態 |
|---|---|---|
| 1 | `backend/app/api/data.py` / `api/qdrant.py` / `core/data_jobs.py` / `core/job_logs.py` に対応する文書が無い | ✅ 解消（4 件を新規作成。§3） |
| 2 | GRACE-Support の設計 3 点（`agent_support_example.md` / `_flow.md` / `_verticals.md`）が `grace/docs/` に置かれたまま。実装は `backend/app/core/support_agent.py` にある | ✅ 解消（`backend/docs/` へ移設。§2.4） |
| 3 | `review_rules_collection.md` にバージョンヘッダーが無い | ✅ 解消（2026-09-15。v1.0 を付与。`backend/docs/` の全 31 文書でヘッダーが揃った） |
| 4 | 文書に未記載の公開シンボルが 24 件あった | ✅ 解消（2026-09-04）。ただし**当時の「100%」は不正確**だった → #6 |
| 5 | `confidence_flow_grace_vs_backend.md` の単数形パス `grace/doc/` | ✅ 解消済み（残る 1 件は「訂正した」旨の**変更履歴の記述**であり違反ではない） |
| 6 | §4.1 が「17 モジュールすべてで 100%」と記録していたが、**実際には 12 件の未記載**があった。当時の監査コミットへ戻して同じスクリプトを流しても同数で、記録が書かれた時点で不正確だった（シンボル数も `core_gates.md` 40 と実際の 49 が食い違い） | ✅ 解消（2026-09-15。12 件を実装から書き起こして追加し、§4.1 を実測値で作り直した） |
| 7 | `core_rulesets.md` §5.4「ルール一覧」が 21 件のままで `yakki-04` / `policy-01` が抜けていた（`41e634d` で他の箇所は 23 に直したが、この表だけ取り残された）。**AST 照合では捕まらない内容の誤り** | ✅ 解消（2026-09-15。23 件へ是正し `always_check` も 6 → 7 へ） |
| 8 | `review_agent_spec.md` §5.3 が `rulesets.py` のキーワード表を複製しており、**キーワードを持つ 15 ルール全部**で語が欠落していた（`yakki-02` は実装 15 語に対し文書 4 語）。`yakki-04` は文書に一度も出てこず、見出しも「21 件」のままだった | ✅ 解消（2026-09-15。**表を削除して正本へのリンクに置換**。同じ表を 2 箇所に持つ限り腐るため） |
| 10 | **設計・フロー文書が 3 層（IPO／フロー／設計）を平坦に混在させており、同じ関数 IPO が 3〜4 重管理になっていた。**`agent_support_example.md` §7.6 は「実コード（`agent_support_example.py`）と突合済み」と書いていたが、その実体は 231 行の CLI ラッパーで、記述された関数（`_answer_gate` / `ActionRequest` 等）は `core/gates.py` / `core/verticals.py` にあった | ✅ 解消（2026-09-15。13 文書を 8 文書＋アーカイブ 2 件へ統合。§2.3 / §8 v1.8） |
| 11 | **ステップ番号の体系が文書ごとに 5 通りあった**（`(0)〜(8)` / `①〜⑥` / `A-1…F-1` / `S1・①〜⑦` / `CLAUDE.md` の `0-(A)…`）。加えて `backend_flow.md` は `STEP_IDS` の 9 段のうち **`analyze`（0-(A)）を丸ごと落としていた**（§5 の「段の網羅」照合で捕まる類） | ✅ 解消（2026-09-15。`CLAUDE.md` §1 の体系へ統一し、`support_flow.md` §4.0 に 0-(A) を新規追加） |
| 12 | `react_processing_flow.md` は `run_dev.sh` 起点の **React（フロントエンド）** の end-to-end フローなのに、本書 §2.3 が「**ReAct** の処理フロー」と説明していた（別物） | ✅ 解消（2026-09-15。`webapp_flow.md` へ改称し説明を是正） |
| 13 | **`api_*.md` / `core_*.md` の 15 文書すべてで、ドキュメント規約 `a_class_method_md_format.md` §6.1 が「必須」としている `### 4.1 使用例`（IPO 詳細セクション冒頭の代表ワークフロー）が欠落していた。** 末尾の `## 5/6. 使用例` は規約上「4.1 に載せきれない応用例のみ」の任意セクションで、代替にならない（`core_data_jobs.md` は末尾のものすら無かった） | ✅ 解消（2026-09-15。15 文書へ新設し、外部依存の要らない例は**実行して出力を確認**した。§8 v1.10） |
| 9 | ローカルで `pytest` が回らない（`google-genai` 等が未導入で 50 件が collection error）。CI は依存を YAML にインライン列挙しており、同じセットをローカルに作る手順が無かった | ✅ 解消（2026-09-15。`requirements-test.txt` を新設して CI と共有する正本にし、手順を CLAUDE.md §2 へ記載。**978 passed, 1 skipped** を実測） |

---

## 2. 文書一覧

### 2.1 API 層（`backend/app/api/`）

> 行数・Ver は 2026-09-15 の実測値（`wc -l` と各文書の Version ヘッダー）。

| 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `api_support.md` | `api/support.py` — 質問応答（SSE でステップ進捗を配信） | 444 | 1.2 | ★★★ |
| `api_review.md` | `api/review.py` — GRACE-Review | 560 | 1.1 | ★★ |
| `api_meta.md` | `api/meta.py` — メタ情報・ヘルスチェック | 416 | 1.2 | ★★ |
| `main.md` | `backend/app/main.py` — アプリ組み立て・ルーター登録 | 521 | 1.3 | ★★ |
| `schemas.md` | `backend/app/schemas.py` — API スキーマ | 1054 | 1.5 | ★★★ |
| `api_data.md` | `api/data.py` — データ準備ジョブ（チャンク化 / 登録 / 削除）の起動・SSE・HITL | 358 | 1.2 | ★★ |
| `api_qdrant.md` | `api/qdrant.py` — Qdrant 参照 API（読み取り専用） | 325 | 1.1 | ★★ |

### 2.2 パイプライン中核（`backend/app/core/`）

| 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `core_support_agent.md` | `core/support_agent.py` — `run_support_agent_core`（Web/CLI 共通の 1 関数） | 720 | 1.3 | ★★★ |
| `core_gates.md` | `core/gates.py` — 質問分析・回答ゲート・④' 判定 | 999 | 1.4 | ★★★ |
| `core_verticals.md` | `core/verticals.py` — `VerticalProfile`（gov / saas / ec） | 588 | 1.3 | ★★ |
| `core_jobs.md` | `core/jobs.py` — ジョブ管理 | 775 | 1.4 | ★★ |
| `core_intervention_bridge.md` | `core/intervention_bridge.py` — HITL の橋渡し | 463 | 1.1 | ★★ |
| `core_review_agent.md` | `core/review_agent.py` | 851 | 1.3 | ★★ |
| `core_review_gates.md` | `core/review_gates.py` | 903 | 1.2 | ★★ |
| `core_rulesets.md` | `core/rulesets.py` | 769 | 1.4 | ★★ |
| `core_data_jobs.md` | `core/data_jobs.py` — 4 種の runner・ステップ定義・CONFIRM の要否 | 492 | 1.3 | ★★ |
| `core_job_logs.md` | `core/job_logs.py` — 既存パッケージの `logging` を進捗イベントへ転送 | 334 | 1.1 | ★★ |

### 2.3 フロー・設計文書（2026-09-15 に 13 → 8 へ統合）

> 行数・Ver は 2026-09-15 の実測値（`wc -l` と各文書の Version ヘッダー）。

**方針**: エージェントごとに **`<agent>_spec.md`（WHY・設計判断）** と
**`<agent>_flow.md`（WHAT・ステップと入出力）** の 2 本立てにし、
**関数の IPO は `core_*.md` / `api_*.md` だけが持つ**（同じ表を 2 箇所に持つと必ず腐るため。§1 問題 #8）。

#### 画面の 4 タブ ↔ 文書（正本は [`webapp_flow.md` §0](./webapp_flow.md#0-タブ--文書の対応)）

| タブ id | ラベル | コア | WHY | WHAT |
|---|---|---|---|---|
| `basic` | 基本版 | `run_support_agent_core(vertical=None)` | `support_spec.md` §7 | `support_flow.md`（0-(B) はスキップ） |
| `support` | GRACE-Support | `run_support_agent_core(vertical=...)` | `support_spec.md` | `support_flow.md` |
| `review` | GRACE-Review | `run_review_agent_core` | `review_spec.md` | `review_flow.md` |
| `data` | データ管理 | `core/data_jobs.py` の 4 runner | `data_pipeline.md` §概要 | `data_pipeline.md` §1〜§4 |

> ⚠️ **`basic` に専用文書を作らない。** `support` と同じコンポーネント・同じコア関数で、
> 差は `vertical` の有無だけ。複製すると片方だけが腐る（§1 問題 #8・#10 と同じ形）。
> **`data` を 2 本に分けない。** `data_pipeline.md` が WHY と WHAT を既に両方持っており、
> Support / Review ほど設計判断の量が無い。

| 文書 | 内容 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `support_spec.md` | GRACE-Support の設計判断（回答ポリシー・HITL・データ契約・0-(A) 複数質問・業界特化・基本版タブ・KPI） | 934 | 1.1 | ★★★ |
| `support_flow.md` | GRACE-Support の処理フロー（0-(A)〜⑥・信頼度フロー比較・付録A CLI・付録B 実行トレース） | 1622 | 2.0 | ★★★ |
| `review_spec.md` | GRACE-Review の設計判断 | 1080 | 1.4 | ★★ |
| `review_flow.md` | GRACE-Review の処理フロー（S1・①〜⑦） | 663 | 1.1 | ★★ |
| `webapp_flow.md` | `run_dev.sh` 起点の end-to-end（ブラウザ → FastAPI → コア → 描画）。**§0 に 4 タブ ↔ 文書の対応表** | 716 | 2.1 | ★★ |
| `data_pipeline.md` | チャンク化・Q/A 生成・Qdrant 登録（付録A: 規程コレクションの準備） | 805 | 1.3 | ★★ |
| `install_and_setup.md` | 環境構築・**起動手順の正本** | 289 | 1.2 | ★★ |

#### 統合の対応表（何がどこへ行ったか）

| 統合前 | 行数 | 統合後 |
|---|---:|---|
| `agent_support_example.md` | 996 | `support_spec.md`（設計章）／`support_flow.md` 付録A（§8 CLI 仕様）。**§7 の関数 IPO は破棄**（`core_gates.md` 等が正本） |
| `agent_support_verticals.md` | 389 | `support_spec.md` §6 |
| `agent_support_example_flow.md` | 455 | `support_flow.md` 付録B |
| `backend_flow.md` | 920 | `support_flow.md`（改称。番号体系を統一し 0-(A) を追加） |
| `confidence_flow_grace_vs_backend.md` | 239 | `support_flow.md` §3.3 |
| `multi_question_handling.md` | 981 | §0・§13 → `support_spec.md` §5／残り（不採用案）→ `archive/` |
| `review_agent_spec.md` | 1072 | `review_spec.md`（改称のみ） |
| `review_rules_collection.md` | 255 | `data_pipeline.md` 付録A |
| `react_processing_flow.md` | 656 | `webapp_flow.md`（改称。`React`/`ReAct` の取り違えを解消） |
| `review_false_positive_todo.md` | 431 | `archive/`（完了済みの調査記録） |
| `main.md` §6.1 | — | `install_and_setup.md` §6 へ一本化（3 重管理だった） |

### 2.4 アーカイブ（`backend/docs/archive/`）

**削除ではなく移動**（`git mv`）。記録としての価値はあるが、実装の正ではない文書。

| 文書 | 内容 | 行数 |
|---|---|---:|
| `archive/multi_question_handling.md` | 複数質問クエリの**採用しなかった案**（§1〜§12 の fan-out 系ロードマップ）。確定仕様は `support_spec.md` §5 | 987 |
| `archive/review_false_positive_todo.md` | GRACE-Review 誤検出の調査記録（§0 の 4 項目はすべて解消済み） | 436 |

---

## 3. 実装カバレッジ

`backend/app/**.py` に対して、対応する文書があるかを機械的に照合した結果。

**2026-09-04 に欠落 4 件を新規作成し、17 モジュールすべてが文書を持つ状態になった。**
AST 列は 2026-09-15 の実測値（全 17 モジュールの網羅は §4.1）。

| 実装 | 文書 | AST 網羅 |
|---|---|---|
| `api/data.py` | `api_data.md`（新規） | 8/8 |
| `api/qdrant.py` | `api_qdrant.md`（新規） | 6/6 |
| `core/data_jobs.py` | `core_data_jobs.md`（新規） | 10/10 |
| `core/job_logs.py` | `core_job_logs.md`（新規） | 7/7 |
| `api/meta.py` / `api/review.py` / `api/support.py` | `api_meta.md` / `api_review.md` / `api_support.md` | — |
| `core/gates.py` / `core/jobs.py` / `core/intervention_bridge.py` | `core_gates.md` / `core_jobs.md` / `core_intervention_bridge.md` | — |
| `core/review_agent.py` / `core/review_gates.py` / `core/rulesets.py` | `core_review_agent.md` / `core_review_gates.md` / `core_rulesets.md` | — |
| `core/support_agent.py` / `core/verticals.py` | `core_support_agent.md` / `core_verticals.md` | — |
| `main.py` / `schemas.py` | `main.md` / `schemas.md` | — |

> 📝 データ管理系（`api/data.py` / `api/qdrant.py` / `core/data_jobs.py`）は
> `data_pipeline.md` が**横断的に**説明している。新規の 3 件はそれと重複させず、
> **モジュール単位の IPO** に徹している（エンドポイントの入出力、ステップ定義、
> runner ごとの処理順、CONFIRM の要否）。

---

## 4. 実装追随状況

### 4.1 公開シンボルの網羅（AST 照合・2026-09-15 実測）

**17 モジュールすべてで 100%。** 下表は `grace/docs/README.md` §4.1 のスクリプトを
全 17 ペアに流した**実測値**である（件数を記憶で書かないこと）。

| 文書 | 公開シンボル | 未記載 |
|---|---:|---:|
| `api_data.md` | 8 | 0 |
| `api_meta.md` | 3 | 0 |
| `api_qdrant.md` | 6 | 0 |
| `api_review.md` | 4 | 0 |
| `api_support.md` | 4 | 0 |
| `core_data_jobs.md` | 10 | 0 |
| `core_gates.md` | 49 | 0 |
| `core_intervention_bridge.md` | 7 | 0 |
| `core_job_logs.md` | 7 | 0 |
| `core_jobs.md` | 18 | 0 |
| `core_review_agent.md` | 32 | 0 |
| `core_review_gates.md` | 16 | 0 |
| `core_rulesets.md` | 13 | 0 |
| `core_support_agent.md` | 8 | 0 |
| `core_verticals.md` | 9 | 0 |
| `main.md` | 0 | 0 |
| `schemas.md` | 29 | 0 |

> ⚠️ **前版（2026-09-04）の表は「100%」と書いていたが、実際には 12 件の未記載が残っていた。**
> 当時の監査コミット（`4e4607d`）へチェックアウトして同じスクリプトを流しても
> `core_gates.md` は **49 件中 7 件未記載**で、`gates.py` はその前（2026-08-30）から
> 変更されていない。つまりこれは**その後のドリフトではなく、記録が書かれた時点で不正確**
> だった（シンボル数も 40 と実際の 49 が食い違っていた）。
> **表を更新するときは必ずスクリプトを流し、出力を貼ること。** 前版の数字を引き写さない。

2026-09-15 の点検で解消した **12 件**:

| 文書 | 件数 | 内容 |
|---|---:|---|
| `core_gates.md` | 7 | `JUDGE_UNEXPECTED_OUTPUT` / `JUDGE_EXCEPTION`、`MULTI_QUESTION_MARKERS` / `MULTI_QUESTION_MIN_MARKS` / `MAX_QUESTION_CLUSTERS`（0-(A) 複数質問検知の閾値）、`_SCOPE_PREFIX_RE` / `OUT_OF_SCOPE_ANSWER_MARKERS`（担当範囲外の判定）。**動作の説明はあったが、それを決める値が書かれていなかった** |
| `core_review_agent.md` | 3 | `_LIST_RE` / `_HEADING_RE` / `_SENTENCE_END_RE` — ① Segment が行の種別を決めている正規表現そのもの |
| `core_rulesets.md` | 2 | `DEFAULT_EVIDENCE_MIN_SCORE` / `DEFAULT_EVIDENCE_TOP_RATIO`。**`RuleSet.evidence_min_score` / `evidence_top_ratio` と `RuleItem.evidence_collections` もフィールドごと未記載**で、② Retrieve の根拠足切りが機構ごと本書から抜けていた |

> 📝 あわせて、AST では捕まらない**内容の誤り**も 1 件見つかった。`core_rulesets.md` §5.4
> 「ルール一覧」が **21 件のまま**で `yakki-04`（安全性の保証表現）と `policy-01`（表示内容と
> 社内規程の不一致）が抜けていた。`41e634d` で他の箇所は 21 → 23 に直したが、この表だけ
> 取り残されていた。**件数を直すときは、件数を書いている箇所を全部 grep すること。**

2026-09-04 の点検で **24 件の未記載**が見つかり、すべて実装から書き起こして追加した。

| 文書 | 件数 | 内容 |
|---|---:|---|
| `schemas.md` | 11 | **データ準備のスキーマがまるごと未記載**（`ChunkingRequest` / `RegisterRequest` / `DeleteCollectionsRequest` / `DataJobStatusResponse` ＋ 参照系 6 つ）と `QuestionClusterModel` |
| `core_gates.md` | 5 | `judge_model`（**`INTENT_MODEL` を直接使ってはいけない**理由つき）/ `_contradicted_claims` / `_abbreviate_reason` / `_count_question_marks` / `_char_bigrams` |
| `core_review_agent.md` | 2 | `_document_segment` / `_is_too_broad`（割合と絶対値の 2 上限を or で見る理由） |
| `core_review_gates.md` | 2 | `select_document_rules`（**表記漏れの判定単位はセグメントではなく文書全体**）/ `_brief` |
| `core_verticals.md` | 2 | `build_closing_instruction`（**位置が結果を変える**）/ `_links_instruction`（**URL を記憶から書かせない**） |
| `core_rulesets.md` | 1 | `RuleItem.retrieval_query()` |
| `core_support_agent.md` | 1 | `QuestionCluster` |

### 4.2 ⚠️ 「コードの日付 > 文書の日付」は追随遅れの証拠にならない

本リポジトリの履歴は途中でまとめてインポートされている。ファイルの「最終コミット日」は
**そのとき内容が書き換わったこと**を意味しないことがある。

実際、`grace/docs` 側の点検では、日付が 2 か月古い `calibration.md` が **15/15 で問題なし**、
逆に日付差の小さい文書に未記載があった。

**日付の比較は当たりを付けるためだけに使い、判断は §5.1 のシンボル網羅と実コードの読解で行う。**

---

## 5. 検証手順

### 5.1 公開シンボルの網羅（AST）

`grace/docs/README.md` §4.1 のスクリプトをそのまま使う（対象パスだけ差し替える）。

### 5.2 CI 4 ゲート（CLAUDE.md §4）

```bash
uv run ruff check . --no-cache
PYTHONPATH=. uv run pytest backend/tests -q
python -m compileall -q -x '\.venv|/\.git/|/logs/' .
cd frontend && npm run lint && npm test && npm run build
```

> ⚠️ **frontend ゲートを忘れない。** API スキーマを変えたら `frontend/src/types.ts` も追随させる。

### 5.3 Mermaid 規約・リンク存在・アンカー解決

`grace/docs/README.md` §4.2（Mermaid 規約）/ §4.3（リンク存在）/ **§4.5（見出しアンカーの解決）** と同じ。
対象を `backend/docs` に読み替えて流す。§4.5 は「節番号を繰り下げた／見出しを言い換えたのに
目次が追随していない」を捕まえる検査で、**リンク存在チェックでは検出できない**
（ファイルは実在し、壊れているのは `#` 以降だけ）。

### 5.4 パイプライン段の網羅

```bash
# 文書が STEP_IDS の 9 段すべてに触れているか
grep -A 12 'STEP_IDS = (' backend/app/core/support_agent.py \
  | grep -oE '"[a-z_]+"' | tr -d '"' | while read -r s; do
    grep -ql "$s" backend/docs/reference/core_support_agent.md || echo "未記載の段: $s"
  done
```

> 📝 `grace_v2_local` では、この照合で **0-(A)「入力・質問分析」の段が丸ごと文書から
> 抜けている**ことが判明した（シンボル網羅 18/51 → 是正後 26/26）。段の抜けは
> 目視では気づきにくい。

---

## 6. 残タスク

| # | タスク | 内容 | 状態 |
|---|---|---|---|
| 1 | ~~欠落 4 件の文書化~~ | **完了**（2026-09-04）。`api_data.md` / `api_qdrant.md` / `core_data_jobs.md` / `core_job_logs.md` を新規作成。AST 網羅はいずれも 100%（§3） | ✅ |
| 2 | ~~GRACE-Support 3 点の移設~~ | **完了**（2026-09-04）。`git mv` で移設し相対リンクを張り替えた（§2.3）。`grace_v2_local` と同じ構成になった | ✅ |
| 3 | ~~追随が遅れている 14 件の突き合わせ~~ | **完了**（2026-09-04）。AST 照合で 24 件の未記載を発見し、すべて解消。17 モジュールで 100%（§4） | ✅ |
| 4 | ~~`review_rules_collection.md` のヘッダー~~ | **完了**（2026-09-15。v1.0 を付与したのち、`data_pipeline.md` 付録A へ統合） | ✅ |
| 5 | ~~リポジトリ直下 `docs/` との重複~~ | **完了**（2026-09-15）。実測した結果、`guardrails.md` / `reasoning_flow.md` / `performance_levers.md` は**複数領域にまたがる横断文書で重複ではなかった**（`core_gates.md` は 1 ファイルの IPO、`guardrails.md` は GA〜G9 の横断ビュー＋失敗時の既定）。実際の重複は `pipelines.md` §3 ↔ `support_spec.md` §7 の 1 件だけで、`pipelines.md` を正本にしてリンクへ置換した。再発防止として [`docs/README.md`](../../docs/README.md) を新設し、配置の境界・重複禁止ルール・全 docs 横断の検出スクリプトを明文化 | ✅ |

---

## 7. 凡例と grep の落とし穴

| 落とし穴 | 中身 |
|---|---|
| **本リポジトリは Anthropic 版** | `install_and_setup.md` の `ANTHROPIC_API_KEY` 必須は**正しい**。`grace_v2_local` では逆に不要（そちらでは誤記として削除した）。持ち込むときに混ぜない |
| **プロバイダ grep の誤検出** | 「Anthropic」「Gemini」で引くと、A/B 比較や Embedding 用途の**正当な記述**も引っかかる。件数を数えず、行を読む |
| **Mermaid grep のスペース** | `classDef default fill: #000`（コロンの後にスペース）は Mermaid としては正しいが §7.6 の grep に引っかからない。`fill: ?#000` で書く |
| **`grace/doc/` の誤検出** | 「`grace/doc/` → `grace/docs/` に訂正」という**変更履歴の記述**は違反ではない |
| **本 README 自体が Mermaid チェックで NG になる** | §7 の凡例に `classDef default fill: #000` という**文字列**が 2 箇所出てくるため、`fc=0 / cd=2` と判定される（実測 2026-09-15）。図は 1 枚も無いので問題ない |
| **grep で見つかる誤りは軽い方** | 深刻なのは**実装を読まないと気づかない**もの: 修正前のコードのままの記述、存在しない実行基盤の「実測値」、丸ごと抜けたパイプライン段、`/api/health` が文書より少ないフィールドしか返さない、といった類 |
| **Web API と CLI は同じ関数を通る** | `uvicorn backend.app.main:app` も `agent_support_example.py` も `run_support_agent_core` を呼ぶ。「Web だけ / CLI だけ」の分岐は無いので、片方で確かめた挙動は他方にも当てはまる |

---

## 8. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.16 | 現在の Embedding の記述を `gemini-embedding-001` から `gemini-embedding-2` へ是正（2026-09-26 に変更。定義は `config.py::ModelConfig.EMBEDDING_MODEL` の 1 箇所）。同じ注記の LLM 既定が `claude-sonnet-4-6`（旧既定）のままだったので `claude-sonnet-5` へ是正 |
| 1.15 | `a_cross_doc_md_format.md` v1.1（種別 C）に準拠（2026-09-24）。ヘッダーの版に対して変更履歴の行が欠けていたため、欠けた版の行を補った |
| 1.14 | reference に上位文書への導線を追加（Phase 3・圧縮は実測により見送り）（本表に記録が無かったため、ヘッダーの版を上げたコミット `3b28ccd` の件名から補った） |
| 1.13 | spec と flow の 2 本立てを解消し系統ごとに 1 本へ統合（Phase 2）（本表に記録が無かったため、ヘッダーの版を上げたコミット `51ec2f6` の件名から補った） |
| 1.12 | 文書を「横断 / 系統別 / 参照」の 3 階建てへ再編（Phase 1）（本表に記録が無かったため、ヘッダーの版を上げたコミット `768bf38` の件名から補った） |
| 1.11 | **直下 `docs/` との重複を解消**（2026-09-15・残タスク #5）。実測の結果、重複していたのは `pipelines.md` §3 ↔ `support_spec.md` §7 の対照表 1 件だけで（v1.9 で本書が足した表が `pipelines.md` の言い換えになっていた）、`pipelines.md` を正本にして `support_spec.md` 側をリンクへ置換した。`guardrails.md` / `reasoning_flow.md` / `performance_levers.md` は複数領域にまたがる横断文書で、`core_*.md`（1 ファイルの IPO）とは軸が違うため**重複ではない**と確認。再発防止に `docs/README.md` を新設 |
| 1.10 | **`api_*.md` / `core_*.md` の 15 文書へ `### N.1 使用例` を新設**（2026-09-15・問題 #13）。ドキュメント規約 §6.1 が必須としている「IPO 詳細セクション冒頭の代表ワークフロー」が 15 文書すべてで欠落しており、長い IPO 詳細へ入る前に「このモジュールをどう呼ぶか」が分からない状態だった。各文書に 1〜3 本ずつ（計 31 本）追加し、**外部依存（実 API キー・Qdrant）が要らない例はすべて実行して出力例に実測値を書いた**。要る 2 例（`run_support_agent_core` / `POST /api/support/query` の一連）は**その旨を明記**して未実行であることを隠していない（CLAUDE.md「やっていない検証をやったと書かない」）。既存の小見出しは N.2 以降へ繰り下げ、目次・内部参照（`core_rulesets` / `core_support_agent` / `core_verticals` の 3 件）も追随させた |
| 1.9 | **画面の 4 タブ ↔ 文書の対応を明示**（2026-09-15）。統合後に「基本版タブとデータ管理タブはどの文書を見ればよいか」が辿れなかったため、(1) `webapp_flow.md` に **§0「タブ ↔ 文書の対応」**を新設（4 タブの画面コンポーネント・コア関数・WHY / WHAT の対応表）、(2) `support_spec.md` に **§7「基本版タブ（`vertical` = None）」**を新設（プロファイル由来の機構が「無し」側に倒れる 9 項目。従来 `docs/pipelines.md` §3 にしか無く Support の設計書から辿れなかった）、(3) 本書 §2.3 に同じ対応表を掲載。あわせて**「基本版に専用文書を作らない」「データ管理を 2 本に分けない」理由**を 3 箇所すべてに明記した（実装が同一・設計判断の量が足りない） |
| 1.8 | **フロー・設計文書 13 件を 8 件＋アーカイブ 2 件へ統合**（2026-09-15・問題 #10 / #11 / #12）。(1) エージェントごとに **`<agent>_spec.md`（WHY）／`<agent>_flow.md`（WHAT）** の 2 本立てへ揃えた（Review 側が既にこの形だったので Support 側を合わせた）。`agent_support_example.md` / `agent_support_verticals.md` / `multi_question_handling.md` §0・§13 → **`support_spec.md`**（新設）、`backend_flow.md` ＋ `confidence_flow_grace_vs_backend.md` ＋ `agent_support_example_flow.md` ＋ CLI 仕様 → **`support_flow.md`**。(2) **関数 IPO の 3〜4 重管理を解消** — `agent_support_example.md` §7.6 は「実コードと突合済み」と書きながら実体を持たない CLI ラッパーを対象にしており、記述された関数は `core/gates.py` / `core/verticals.py` にあった。フロー文書・設計書から IPO を外し、`core_*.md` へのリンクに置換した（問題 #8 と同じ処方箋）。(3) **ステップ番号を `CLAUDE.md` §1 の体系へ統一**し、`backend_flow.md` が落としていた **0-(A) `analyze`** を `support_flow.md` §4.0 として新規に書き起こした。(4) `react_processing_flow.md` → **`webapp_flow.md`**（`React`/`ReAct` の取り違えを解消）、`review_agent_spec.md` → **`review_spec.md`**、`review_rules_collection.md` → `data_pipeline.md` 付録A、`main.md` §6.1 の起動手順 → `install_and_setup.md` §6 へ一本化。(5) 完了済みの記録 2 件を **`archive/`** へ `git mv`（削除はしていない）。(6) 統合中に判明した**実装との食い違い 4 件**（存在しない `ActionTool`、追随できていない dataclass フィールド表、「5 フィールド」→ 実測 7、`build_prompt_addendum` → `build_closing_instruction`）を是正。被参照 41 ファイル（ソースコメント・テスト・フロント・`grace/` 側文書）のパスと節番号を張り替え、**リンク切れ 0** を確認 |
| 1.7 | **設計・フロー文書の未修正 4 件を解消し、ローカルで pytest が回るようにした**（2026-09-15・問題 #3 / #8 / #9）。(1) `review_agent_spec.md` §5.3 の**キーワード表を削除して正本へのリンクに置換**——15 ルール全部で語が腐り `yakki-04` が丸ごと欠落していた。同じ表を 2 箇所に持つ限り必ず腐るため、本書は法令別の件数と判定方式の要約だけを持つ形にした。(2) `core_rulesets.md` §4.2 の「21 件程度」を 23 件へ（v1.2 で表は直したが grep しきれず取り残していた）。(3) `review_rules_collection.md` の CSV 行数を 22 → **23 行**へ（`build_rows()` はフィルタせず `ruleset.rules` を回す）。(4) 同ファイルに Version ヘッダーを付与（問題 #3）。(5) **`requirements-test.txt` を新設**し CI（`pytest (backend)` ジョブ）と共有する唯一の正本にした。従来は CI の YAML にインライン列挙しており、ローカルに同じ環境を作る手順が無かった |
| 1.6 | **backend 固有の設計文書 2 件をリポジトリ直下 `docs/` から移設**（2026-09-15）。`multi_question_handling.md`（0-(A) 複数質問・`core/gates.py` / `core/support_agent.py`）と `review_false_positive_todo.md`（Review 誤検出の調査記録・`core/rulesets.py` / `core/review_gates.py`）。いずれも対象が `backend/app/core/` に閉じており、CLAUDE.md §9.1 の「backend は `backend/docs/`」に該当する。被参照 18 ファイル（ソースコメント・テスト・フロント含む）のパスを張り替えた。横断文書 7 件は frontend や `grace/` にもまたがるため直下 `docs/` に残した。あわせて **`### 2.3` が 2 つあった採番ミス**を是正（GRACE-Support の設計書を §2.4 へ） |
| 1.5 | **未記載シンボル 12 件と内容の誤り 1 件を解消し、§4.1 を実測で作り直した**（2026-09-15・問題 #6 / #7）。前版の「17 モジュールすべてで 100%」は**書かれた時点で不正確**で、当時の監査コミット（`4e4607d`）へ戻して同じスクリプトを流しても `core_gates.md` は 49 件中 7 件未記載だった（記録のシンボル数 40 も実際の 49 と食い違い）。`core_gates.md` 7 件（複数質問検知・担当範囲外の判定の閾値）/ `core_review_agent.md` 3 件（① Segment の分割正規表現）/ `core_rulesets.md` 2 件（② Retrieve の根拠足切り。`RuleSet.evidence_min_score` / `evidence_top_ratio` と `RuleItem.evidence_collections` も**フィールドごと**未記載だった）を実装から書き起こして追加。あわせて AST では捕まらない内容の誤り——`core_rulesets.md` §5.4 のルール一覧が 21 件のままで `yakki-04` / `policy-01` が抜けていた——も是正した。§3 の AST 列も実測へ揃え、§5.3 に アンカー解決の検査を追加 |
| 1.4 | **目次のアンカー 1 件を見出しへ是正**（2026-09-14）。§3 の見出しが `## 3. 実装カバレッジ` へ変わった際（v1.1 で「欠落一覧」→「カバレッジ表」に書き換え）、**目次だけが旧題のまま**残り `#3-実装カバレッジ欠落している文書` が解決しなくなっていた |
| 1.3 | **GRACE-Support 3 点を `grace/docs/` から移設**（2026-09-04）。実装が `backend/app/core/support_agent.py` にあるため。§2.4（当時は §2.3）を新設し、相対リンクの張り替え方針も記録。これで `grace_v2_local` と同じ構成になった |
| 1.2 | **未記載シンボル 24 件を解消**（2026-09-04）。17 モジュールすべてで AST 網羅 **100%** に到達。最大は `schemas.md` の 11 件で、**データ準備のスキーマがまるごと未記載**だった（API は既にあるのに型の説明が無い状態）。§4 を「日付比較」から「AST 網羅」の記録へ書き換え、日付比較が追随遅れの証拠にならない理由も明記 |
| 1.1 | **欠落していた 4 件を新規作成**（2026-09-04）: `api_data.md` / `api_qdrant.md` / `core_data_jobs.md` / `core_job_logs.md`。これで `backend/app/**.py` の 17 モジュールすべてが文書を持つ。§3 を「欠落一覧」から「カバレッジ表」へ書き換えた |
| 1.0 | 初版作成。文書 21 件＋本書の一覧、`backend/app/**.py` との機械的照合（**4 件の欠落**を検出）、コード最終コミット日との追随比較（14 件が遅れ）、検証手順 4 種（AST シンボル網羅・CI 4 ゲート・Mermaid/リンク・パイプライン段の網羅）、残タスク 4 件、grep の落とし穴 6 件を整備 |
