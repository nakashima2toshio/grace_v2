# backend/docs 棚卸し

**Version 1.0** | 最終更新: 2026-09-04

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
| 1 | `backend/app/api/data.py` / `api/qdrant.py` / `core/data_jobs.py` / `core/job_logs.py` に対応する文書が無い | ⏳ 未対応（§3） |
| 2 | GRACE-Support の設計 3 点（`agent_support_example.md` / `_flow.md` / `_verticals.md`）が `grace/docs/` に置かれたまま。実装は `backend/app/core/support_agent.py` にある | ⏳ 未対応（§6 の #2） |
| 3 | `review_rules_collection.md` にバージョンヘッダーが無い | ⏳ 未対応（§6 の #4） |
| 4 | 主要文書 14 件が、対応するコードの最終更新より古い | ⏳ 未対応（§4） |
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

---

## 3. 実装カバレッジ（欠落している文書）

`backend/app/**.py` に対して、対応する文書があるかを機械的に照合した結果。

| 実装 | 期待される文書 | 状態 |
|---|---|---|
| `api/data.py` | `backend/docs/api_data.md` | ❌ **無い** |
| `api/qdrant.py` | `backend/docs/api_qdrant.md` | ❌ **無い** |
| `core/data_jobs.py` | `backend/docs/core_data_jobs.md` | ❌ **無い**（`data_pipeline.md` が部分的に触れている） |
| `core/job_logs.py` | `backend/docs/core_job_logs.md` | ❌ **無い** |
| 上記以外の 13 モジュール | — | ✅ あり |

> 📝 データ管理系（`api/data.py` / `api/qdrant.py` / `core/data_jobs.py`）は
> `data_pipeline.md` が横断的に説明しているが、**モジュール単位の IPO 文書は無い**。
> `grace_v2_local` 側は同じ構成で `backend/docs/data_pipeline.md` を持つのみなので、
> こちらだけの欠落ではない。

---

## 4. 実装追随状況

対応するコードの最終コミット日と、文書の「最終更新」の比較（2026-09-04 時点）。

| 文書 | コード | 文書 | 差 |
|---|---|---|---|
| `core_intervention_bridge.md` | 2026-08-29 | 2026-07-15 | **約 1.5 か月** |
| `core_review_agent.md` | 2026-08-30 | 2026-07-29 | 約 1 か月 |
| `core_review_gates.md` | 2026-08-30 | 2026-07-29 | 約 1 か月 |
| `core_rulesets.md` | 2026-08-20 | 2026-07-29 | 約 1 か月 |
| `main.md` | 2026-08-11 | 2026-07-29 | 約 2 週間 |
| `api_meta.md` | 2026-08-11 | 2026-07-29 | 約 2 週間 |
| `api_review.md` | 2026-08-11 | 2026-07-29 | 約 2 週間 |
| `core_gates.md` | 2026-08-30 | 2026-08-01 | 約 1 か月 |
| `core_support_agent.md` | 2026-08-30 | 2026-08-01 | 約 1 か月 |
| `core_verticals.md` | 2026-08-30 | 2026-08-01 | 約 1 か月 |
| `api_support.md` | 2026-08-29 | 2026-08-01 | 約 4 週間 |
| `core_jobs.md` | 2026-08-29 | 2026-08-01 | 約 4 週間 |
| `schemas.md` | 2026-08-29 | 2026-08-01 | 約 4 週間 |
| `data_pipeline.md` | 2026-08-11 | 2026-08-05 | 約 1 週間 |

> ⚠️ **日付の差は「ズレている」ことの証明ではない。** コード側の変更が文書に無関係な場合もある。
> 差が大きいものから §5.1 のシンボル網羅チェックを当てて、実際にズレているかを確かめる。

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
| 1 | 欠落 4 件の文書化 | `api_data.md` / `api_qdrant.md` / `core_data_jobs.md` / `core_job_logs.md`（§3） | ⏳ |
| 2 | GRACE-Support 3 点の移設判断 | `agent_support_example.md` / `_flow.md` / `_verticals.md` は `grace/docs/` にあるが、実装は `backend/app/core/support_agent.py`。`grace_v2_local` は `backend/docs/` へ移設済み。**移設すると相対リンクが全滅する**ので、リンク張り替えとセットで行う | ⏳ |
| 3 | 追随が遅れている 14 件の突き合わせ | §4 の差が大きいもの（`core_intervention_bridge.md` / GRACE-Review 系 3 件）から §5.1 を当てる | ⏳ |
| 4 | `review_rules_collection.md` のヘッダー | この 1 件だけ `**Version X.X**` ヘッダーが無い | ⏳ |

---

## 7. 凡例と grep の落とし穴

| 落とし穴 | 中身 |
|---|---|
| **本リポジトリは Anthropic 版** | `install_and_setup.md` の `ANTHROPIC_API_KEY` 必須は**正しい**。`grace_v2_local` では逆に不要（そちらでは誤記として削除した）。持ち込むときに混ぜない |
| **プロバイダ grep の誤検出** | 「Anthropic」「Gemini」で引くと、A/B 比較や Embedding 用途の**正当な記述**も引っかかる。件数を数えず、行を読む |
| **Mermaid grep のスペース** | `classDef default fill: #000`（コロンの後にスペース）は Mermaid としては正しいが §7.6 の grep に引っかからない。`fill: ?#000` で書く |
| **`grace/doc/` の誤検出** | 「`grace/doc/` → `grace/docs/` に訂正」という**変更履歴の記述**は違反ではない |
| **grep で見つかる誤りは軽い方** | 深刻なのは**実装を読まないと気づかない**もの: 修正前のコードのままの記述、存在しない実行基盤の「実測値」、丸ごと抜けたパイプライン段、`/api/health` が文書より少ないフィールドしか返さない、といった類 |
| **Web API と CLI は同じ関数を通る** | `uvicorn backend.app.main:app` も `agent_support_example.py` も `run_support_agent_core` を呼ぶ。「Web だけ / CLI だけ」の分岐は無いので、片方で確かめた挙動は他方にも当てはまる |

---

## 8. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.0 | 初版作成。文書 21 件＋本書の一覧、`backend/app/**.py` との機械的照合（**4 件の欠落**を検出）、コード最終コミット日との追随比較（14 件が遅れ）、検証手順 4 種（AST シンボル網羅・CI 4 ゲート・Mermaid/リンク・パイプライン段の網羅）、残タスク 4 件、grep の落とし穴 6 件を整備 |
