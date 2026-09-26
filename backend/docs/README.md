# backend/docs — 文書の地図

**Version 2.4** | 最終更新: 2026-09-26

---

`backend/`（FastAPI + パイプライン中核）の**入口**。どの文書に何が書いてあるか、
どの順に読むかだけを示す。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-5`（軽量
> `claude-haiku-4-5-20251001`）で `ANTHROPIC_API_KEY` が必須、Embedding のみ
> Gemini `gemini-embedding-2`（3072 次元・`GOOGLE_API_KEY`）。姉妹リポジトリ
> `grace_v2_local` は Ollama 版で**表記が逆**なので、あちらの文書を持ち込まない。

> **関連**: `grace/` 側は [`grace/docs/README.md`](../../grace/docs/README.md)、
> フロントは [`frontend/docs/README.md`](../../frontend/docs/README.md)、
> 横断の設計メモは [`docs/README.md`](../../docs/README.md)。

---

## 目次

- [1. 読む順路](#1-読む順路)
- [2. 文書一覧](#2-文書一覧)
- [3. 目的別の早見表](#3-目的別の早見表)
- [4. 文書を書くときの規約](#4-文書を書くときの規約)
- [5. 変更履歴](#5-変更履歴)

---

## 1. 読む順路

```
architecture.md            層構造・モジュール責務・外部境界（まずここ）
  └ job_runtime.md         ジョブ・SSE・HITL の共有基盤（3 系統に共通・必読）
      ├ support_flow.md    担当する系統だけ読む
      ├ review_flow.md
      └ data_pipeline.md
api_contract.md            フロント / API 利用者はここから
config_and_providers.md    モデル・API キーを触る前に
pitfalls.md                コードを触る前に
reference/*.md             引く（通読しない）
```

---

## 2. 文書一覧

### 2.1 横断（backend 全体を理解する）

| 文書 | 種別 | 何が書いてあるか |
|---|:--:|---|
| [`architecture.md`](./architecture.md) | A | 層構造、17 モジュールの責務と行数、**backend が持たないもの（外部境界）**、依存の向き、リクエストが通る経路 |
| [`job_runtime.md`](./job_runtime.md) | A | **3 系統が共有する実行基盤の正本。** ジョブのライフサイクル、イベントのリプレイ、runner 注入、HITL の橋渡し、ログ転送、ローカル専用であることの制約 |
| [`api_contract.md`](./api_contract.md) | A | 全 23 エンドポイント、SSE のワイヤ形式、HTTP ステータスの使い分け、`frontend/src/types.ts` との対応 |
| [`config_and_providers.md`](./config_and_providers.md) | A | **モデル名の 3 本の解決経路**、`judge_model()` / `detect_model()`、API キーのガード位置 |
| [`pitfalls.md`](./pitfalls.md) | B | 非自明な設計判断・過去に壊れた箇所・**直してはいけないもの** |

### 2.2 系統別（何をどう判断しているか）

| 文書 | 種別 | 対象 |
|---|:--:|---|
| [`support_flow.md`](./support_flow.md) | A | GRACE-Support の処理フロー（0-(A)〜⑥）と設計判断。**WHY と HOW が 1 本**（v3.0 で `support_spec.md` を統合） |
| [`review_flow.md`](./review_flow.md) | A | GRACE-Review の処理フロー（S1・①〜⑦）と設計判断（v2.0 で `review_spec.md` を統合） |
| [`verticals_and_rulesets.md`](./verticals_and_rulesets.md) | A | 業界プロファイル（gov / saas / ec）とルールセット（ec_ad）の**カタログ**・増やし方 |
| [`data_pipeline.md`](./data_pipeline.md) | A | チャンク化 → Q/A 生成 → Qdrant 登録（付録A: 規程コレクションの準備） |
| [`webapp_flow.md`](./webapp_flow.md) | A | `run_dev.sh` 起点の end-to-end（ブラウザ → FastAPI → コア → 描画） |

### 2.3 モジュール参照（`reference/`）— 引く用

種別はすべて E（`a_class_method_md_format.md` の IPO 形式。使用例は IPO 詳細の冒頭 `### 4.1 使用例`）。

各文書の冒頭に**位置づけと上位文書への導線**がある（どの設計文書が「なぜ」の正本かを示す）。
公開シンボルの網羅は AST で検証済み（**223 シンボル / 未記載 0**・実測 2026-09-16）。

| 対象 | 文書 |
|---|---|
| `backend/app/main.py` | [`reference/main.md`](./reference/main.md) |
| `backend/app/schemas.py` | [`reference/schemas.md`](./reference/schemas.md) |
| `api/support.py` / `api/review.py` / `api/data.py` / `api/qdrant.py` / `api/meta.py` | [`reference/api_support.md`](./reference/api_support.md)・[`api_review.md`](./reference/api_review.md)・[`api_data.md`](./reference/api_data.md)・[`api_qdrant.md`](./reference/api_qdrant.md)・[`api_meta.md`](./reference/api_meta.md) |
| `core/support_agent.py` / `gates.py` / `verticals.py` | [`reference/core_support_agent.md`](./reference/core_support_agent.md)・[`core_gates.md`](./reference/core_gates.md)・[`core_verticals.md`](./reference/core_verticals.md) |
| `core/review_agent.py` / `review_gates.py` / `rulesets.py` | [`reference/core_review_agent.md`](./reference/core_review_agent.md)・[`core_review_gates.md`](./reference/core_review_gates.md)・[`core_rulesets.md`](./reference/core_rulesets.md) |
| `core/jobs.py` / `intervention_bridge.py` / `job_logs.py` / `data_jobs.py` | [`reference/core_jobs.md`](./reference/core_jobs.md)・[`core_intervention_bridge.md`](./reference/core_intervention_bridge.md)・[`core_job_logs.md`](./reference/core_job_logs.md)・[`core_data_jobs.md`](./reference/core_data_jobs.md) |

### 2.4 運用・記録

| 文書 | 種別 | 内容 |
|---|:--:|---|
| [`install_and_setup.md`](./install_and_setup.md) | B | 環境構築・**起動手順の正本** |
| [`testing.md`](./testing.md) | B | `backend/tests` の地図・どこを触ったらどれを流すか・CI の 4 ゲート |
| [`migration_plan.md`](./migration_plan.md) | C | 文書再編の計画（Phase 1 完了 / Phase 2・3 の予定） |
| [`docs_audit.md`](./docs_audit.md) | C | 棚卸し・実装追随の照合結果・検証スクリプト・残タスク |
| [`archive/`](./archive/) | — | 記録としては残すが実装の正ではない文書 |

---

## 3. 目的別の早見表

| やりたいこと | 読む文書 |
|---|---|
| backend の全体像を掴む | `architecture.md` |
| SSE / ジョブ / HITL の仕組みを知る | `job_runtime.md` |
| 新しいエンドポイントを足す | `api_contract.md` → `job_runtime.md` §3 → `reference/api_*.md` |
| 新しいジョブ種別を足す | `job_runtime.md` §3・§8 → `reference/core_data_jobs.md` |
| 回答が escalate に倒れる理由を追う | `support_flow.md` → `reference/core_gates.md` |
| 指摘が出ない / 誤検知する理由を追う | `review_flow.md` → `reference/core_review_gates.md` |
| 業界プロファイル / ルールセットを増やす | `verticals_and_rulesets.md` §3 |
| テストを足す・どれを流すか調べる | `testing.md` |
| 既定モデルを変える | `config_and_providers.md` §6 |
| 起動できない・キーが無い | `install_and_setup.md` → `config_and_providers.md` §4 |
| 触る前に地雷を確認する | `pitfalls.md` |

---

## 4. 文書を書くときの規約

| 対象 | 仕様書 |
|---|---|
| Python モジュール（IPO 形式） | `.claude/skills/grace-agent-docs/a_class_method_md_format.md` |
| React コンポーネント | `.claude/skills/grace-agent-docs/a_react_page_md_format.md` |
| 設計・フロー・API 契約・手順・索引（IPO 以外。上表の種別 A / B / C） | `.claude/skills/grace-agent-docs/a_cross_doc_md_format.md`（A: 概要に主な責務・各責務対応のモジュール・3 層の構成図／B: 概要に結論・対象モジュール／C: 目次と変更履歴） |
| 単体テスト（SAE 形式） | `.claude/skills/grace-agent-tests/a_test_md_format.md` |
| Mermaid のスタイル | `CLAUDE.md` §7（黒背景・白文字が**必須**） |

- 全文書に `**Version X.Y** | 最終更新: YYYY-MM-DD` のヘッダーを付ける
- **実装の表・定数を文書へ複製しない**（複製は必ず腐る。リンクで正本を指す）
- **テスト件数は実行して実測値を書く**（記憶で書かない）

---

## 5. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 2.4 | 2026-09-26 | 現在の Embedding の記述を `gemini-embedding-001` から `gemini-embedding-2` へ是正（2026-09-26 に変更。定義は `config.py::ModelConfig.EMBEDDING_MODEL` の 1 箇所） |
| 2.3 | 2026-09-24 | `a_cross_doc_md_format.md` v1.1（種別 C）に準拠（2026-09-24）。目次を追加し、§2 の各表へ「種別」列（A / B / C、`reference/` は E）を足し、§4 の規約表に横断文書フォーマットを追加した |
| 2.2 | 2026-09-16 | **Phase 3 を反映**。`reference/` の 17 文書に位置づけヘッダーが付いたことを §2.3 に明記した（圧縮は実測の結果不要と判断。[`migration_plan.md` §4](./migration_plan.md)） |
| 2.1 | 2026-09-16 | **Phase 2 を反映**。`support_spec.md` / `review_spec.md` を各 `*_flow.md` へ統合し、`verticals_and_rulesets.md` と `testing.md` を新設した（[`migration_plan.md` §3](./migration_plan.md)） |
| 2.0 | 2026-09-16 | 棚卸し内容を `docs_audit.md` へ分離し、README を**地図**に作り替えた。モジュール文書 17 本を `reference/` へ移動し、横断文書 5 本を新設した |
| 1.11 以前 | 〜2026-09-15 | [`docs_audit.md`](./docs_audit.md) の変更履歴を参照 |
