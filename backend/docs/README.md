# backend/docs 棚卸し

**Version 1.3** | 最終更新: 2026-09-04

`backend/`（FastAPI + パイプライン中核）のドキュメント一覧と、実装への追随状況・
欠落・残タスク・検証手順をまとめる。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-4-6`（軽量 `claude-haiku-4-5-20251001`）で
> `ANTHROPIC_API_KEY` が**必須**、Embedding のみ Gemini `gemini-embedding-001`（3072 次元・`GOOGLE_API_KEY`）。
> 姉妹リポジトリ `grace_v2_local` は Ollama 版で LLM 用の API キーが不要。**表記が逆**なので、
> あちらの文書をそのまま持ち込まない（CLAUDE.md §3・§5）。

> **関連**: `grace/` 側の棚卸しは [`grace/docs/README.md`](../../grace/docs/README.md)。

---

## 目次

- [1. 現在わかっている問題](#1-現在わかっている問題)
- [2. 文書一覧](#2-文書一覧)
- [3. 実装カバレッジ（欠落している文書）](#3-実装カバレッジ欠落している文書)
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
| 2 | GRACE-Support の設計 3 点（`agent_support_example.md` / `_flow.md` / `_verticals.md`）が `grace/docs/` に置かれたまま。実装は `backend/app/core/support_agent.py` にある | ✅ 解消（`backend/docs/` へ移設。§2.3） |
| 3 | `review_rules_collection.md` にバージョンヘッダーが無い | ⏳ 未対応（§6 の #4） |
| 4 | 文書に未記載の公開シンボルが 24 件あった | ✅ 解消（**17 モジュールすべてで AST 網羅 100%**。§4） |
| 5 | `confidence_flow_grace_vs_backend.md` の単数形パス `grace/doc/` | ✅ 解消済み（残る 1 件は「訂正した」旨の**変更履歴の記述**であり違反ではない） |

---

## 2. 文書一覧

### 2.1 API 層（`backend/app/api/`）

| 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `api_support.md` | `api/support.py` — 質問応答（SSE でステップ進捗を配信） | 376 | 1.1 | ★★★ |
| `api_review.md` | `api/review.py` — GRACE-Review | 494 | 1.0 | ★★ |
| `api_meta.md` | `api/meta.py` — メタ情報・ヘルスチェック | 364 | 1.1 | ★★ |
| `main.md` | `backend/app/main.py` — アプリ組み立て・ルーター登録 | 541 | 1.2 | ★★ |
| `schemas.md` | `backend/app/schemas.py` — API スキーマ | 818 | 1.2 | ★★★ |
| `api_data.md` | `api/data.py` — データ準備ジョブ（チャンク化 / 登録 / 削除）の起動・SSE・HITL | 283 | 1.0 | ★★ |
| `api_qdrant.md` | `api/qdrant.py` — Qdrant 参照 API（読み取り専用） | 269 | 1.0 | ★★ |

### 2.2 パイプライン中核（`backend/app/core/`）

| 文書 | 対象 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `core_support_agent.md` | `core/support_agent.py` — `run_support_agent_core`（Web/CLI 共通の 1 関数） | 637 | 1.1 | ★★★ |
| `core_gates.md` | `core/gates.py` — 質問分析・回答ゲート・④' 判定 | 786 | 1.1 | ★★★ |
| `core_verticals.md` | `core/verticals.py` — `VerticalProfile`（gov / saas / ec） | 485 | 1.1 | ★★ |
| `core_jobs.md` | `core/jobs.py` — ジョブ管理 | 668 | 1.2 | ★★ |
| `core_intervention_bridge.md` | `core/intervention_bridge.py` — HITL の橋渡し | 407 | 1.0 | ★★ |
| `core_review_agent.md` | `core/review_agent.py` | 738 | 1.0 | ★★ |
| `core_review_gates.md` | `core/review_gates.py` | 781 | 1.0 | ★★ |
| `core_rulesets.md` | `core/rulesets.py` | 644 | 1.0 | ★★ |
| `core_data_jobs.md` | `core/data_jobs.py` — 3 種の runner・ステップ定義・CONFIRM の要否 | 362 | 1.0 | ★★ |
| `core_job_logs.md` | `core/job_logs.py` — 既存パッケージの `logging` を進捗イベントへ転送 | 298 | 1.0 | ★★ |

### 2.3 フロー・設計文書

| 文書 | 内容 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `backend_flow.md` | backend 全体の処理フロー | 920 | 1.1 | ★★★ |
| `review_agent_spec.md` | GRACE-Review の仕様 | 1081 | 1.1 | ★★ |
| `review_flow.md` | GRACE-Review の処理フロー | 661 | 1.0 | ★★ |
| `review_rules_collection.md` | レビュー規則の収集 | 245 | — | ★ |
| `react_processing_flow.md` | ReAct の処理フロー | 656 | 1.0 | ★★ |
| `confidence_flow_grace_vs_backend.md` | `grace/` 側と backend 側の信頼度フロー比較 | 239 | 1.1 | ★★ |
| `data_pipeline.md` | チャンク化・Q/A 生成・Qdrant 登録 | 523 | 1.1 | ★★ |
| `install_and_setup.md` | 環境構築 | 285 | 1.1 | ★★ |

### 2.3 GRACE-Support の設計書（2026-09-04 に `grace/docs/` から移設）

実装が `backend/app/core/support_agent.py` にあるため、`grace/docs/` から移してきた。

| 文書 | 内容 | 行数 | Ver | 重要度 |
|---|---|---:|---|---|
| `agent_support_example.md` | GRACE-Support 本体の設計書（v1〜v3 ＋ 業界特化） | 993 | 1.2 | ★★★ |
| `agent_support_example_flow.md` | 1 コマンドの実行トレース（`--vertical gov` の IN/OUT データフロー） | 455 | 1.2 | ★★ |
| `agent_support_verticals.md` | 業界特化（gov / saas / ec）の `VerticalProfile` 設計 | 392 | 2.0 | ★★ |

> 📝 **移設にあたって相対リンクを張り替えた。**
> 3 件どうしのリンクは `./` のまま有効。`grace/docs/` 側（`grace_core.md` / `grace_core_flow.md`）
> へは `../../grace/docs/` へ、`grace/step_trace/` からこの 3 件へのリンクは
> `../../backend/docs/` / `../../../backend/docs/` へ直した。**リンク切れ 0 を確認済み。**

---

## 3. 実装カバレッジ

`backend/app/**.py` に対して、対応する文書があるかを機械的に照合した結果。

**2026-09-04 に欠落 4 件を新規作成し、17 モジュールすべてが文書を持つ状態になった。**

| 実装 | 文書 | AST 網羅 |
|---|---|---|
| `api/data.py` | `api_data.md`（新規） | 7/7 |
| `api/qdrant.py` | `api_qdrant.md`（新規） | 6/6 |
| `core/data_jobs.py` | `core_data_jobs.md`（新規） | 14/14 |
| `core/job_logs.py` | `core_job_logs.md`（新規） | 9/9 |
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

### 4.1 公開シンボルの網羅（AST 照合・2026-09-04）

**17 モジュールすべてで 100%。**

| 文書 | 公開シンボル | 未記載 |
|---|---:|---:|
| `api_data.md` | 6 | 0 |
| `api_meta.md` | 3 | 0 |
| `api_qdrant.md` | 6 | 0 |
| `api_review.md` | 4 | 0 |
| `api_support.md` | 4 | 0 |
| `core_data_jobs.md` | 8 | 0 |
| `core_gates.md` | 40 | 0 |
| `core_intervention_bridge.md` | 5 | 0 |
| `core_job_logs.md` | 6 | 0 |
| `core_jobs.md` | 15 | 0 |
| `core_review_agent.md` | 21 | 0 |
| `core_review_gates.md` | 15 | 0 |
| `core_rulesets.md` | 8 | 0 |
| `core_support_agent.md` | 6 | 0 |
| `core_verticals.md` | 6 | 0 |
| `main.md` | 0 | 0 |
| `schemas.md` | 27 | 0 |

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

### 5.3 Mermaid 規約・リンク存在確認

`grace/docs/README.md` §4.2 / §4.3 と同じ（対象を `backend/docs` に読み替える）。

### 5.4 パイプライン段の網羅

```bash
# 文書が STEP_IDS の 9 段すべてに触れているか
grep -A 12 'STEP_IDS = (' backend/app/core/support_agent.py \
  | grep -oE '"[a-z_]+"' | tr -d '"' | while read -r s; do
    grep -ql "$s" backend/docs/core_support_agent.md || echo "未記載の段: $s"
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
| 4 | `review_rules_collection.md` のヘッダー | この 1 件だけ `**Version X.X**` ヘッダーが無い | ⏳ |

---

## 7. 凡例と grep の落とし穴

| 落とし穴 | 中身 |
|---|---|
| **本リポジトリは Anthropic 版** | `install_and_setup.md` の `ANTHROPIC_API_KEY` 必須は**正しい**。`grace_v2_local` では逆に不要（そちらでは誤記として削除した）。持ち込むときに混ぜない |
| **プロバイダ grep の誤検出** | 「Anthropic」「Gemini」で引くと、A/B 比較や Embedding 用途の**正当な記述**も引っかかる。件数を数えず、行を読む |
| **Mermaid grep のスペース** | `classDef default fill: #000`（コロンの後にスペース）は Mermaid としては正しいが §7.6 の grep に引っかからない。`fill: ?#000` で書く |
| **`grace/doc/` の誤検出** | 「`grace/doc/` → `grace/docs/` に訂正」という**変更履歴の記述**は違反ではない |
| **本 README 自体が Mermaid チェックで NG になる** | §7 の凡例に `classDef default fill: #000` という**文字列**が出てくるため、`fc=0 / cd=1` と判定される。図は 1 枚も無いので問題ない |
| **grep で見つかる誤りは軽い方** | 深刻なのは**実装を読まないと気づかない**もの: 修正前のコードのままの記述、存在しない実行基盤の「実測値」、丸ごと抜けたパイプライン段、`/api/health` が文書より少ないフィールドしか返さない、といった類 |
| **Web API と CLI は同じ関数を通る** | `uvicorn backend.app.main:app` も `agent_support_example.py` も `run_support_agent_core` を呼ぶ。「Web だけ / CLI だけ」の分岐は無いので、片方で確かめた挙動は他方にも当てはまる |

---

## 8. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.3 | **GRACE-Support 3 点を `grace/docs/` から移設**（2026-09-04）。実装が `backend/app/core/support_agent.py` にあるため。§2.3 を新設し、相対リンクの張り替え方針も記録。これで `grace_v2_local` と同じ構成になった |
| 1.2 | **未記載シンボル 24 件を解消**（2026-09-04）。17 モジュールすべてで AST 網羅 **100%** に到達。最大は `schemas.md` の 11 件で、**データ準備のスキーマがまるごと未記載**だった（API は既にあるのに型の説明が無い状態）。§4 を「日付比較」から「AST 網羅」の記録へ書き換え、日付比較が追随遅れの証拠にならない理由も明記 |
| 1.1 | **欠落していた 4 件を新規作成**（2026-09-04）: `api_data.md` / `api_qdrant.md` / `core_data_jobs.md` / `core_job_logs.md`。これで `backend/app/**.py` の 17 モジュールすべてが文書を持つ。§3 を「欠落一覧」から「カバレッジ表」へ書き換えた |
| 1.0 | 初版作成。文書 21 件＋本書の一覧、`backend/app/**.py` との機械的照合（**4 件の欠落**を検出）、コード最終コミット日との追随比較（14 件が遅れ）、検証手順 4 種（AST シンボル網羅・CI 4 ゲート・Mermaid/リンク・パイプライン段の網羅）、残タスク 4 件、grep の落とし穴 6 件を整備 |
