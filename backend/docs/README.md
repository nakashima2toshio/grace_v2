# backend/docs — 文書の地図

**Version 2.7** | 最終更新: 2026-10-08

---

`backend/`（FastAPI + パイプライン中核）の**入口**。どの文書に何が書いてあるか、
どの順に読むかだけを示す。

> ⚠️ **本リポジトリは Anthropic 版。** LLM は `claude-sonnet-5`（軽量
> `claude-haiku-5-5`）で `ANTHROPIC_API_KEY` が必須、Embedding のみ
> Gemini `gemini-embedding-001`（3072 次元・`GOOGLE_API_KEY`）。姉妹リポジトリ
> `grace_v2_local` は Ollama 版で**表記が逆**なので、あちらの文書を持ち込まない。

> **関連**: `grace/` 側は [`grace/docs/README.md`](../../grace/docs/README.md)、
> フロントは [`frontend/docs/README.md`](../../frontend/docs/README.md)、
> 横断の設計メモは [`docs/README.md`](../../docs/README.md)。

---

## 目次

- [1. backend の責務](#1-backend-の責務)
- [2. 読む順路](#2-読む順路)
- [3. 文書一覧](#3-文書一覧)
- [4. 目的別の早見表](#4-目的別の早見表)
- [5. 文書を書くときの規約](#5-文書を書くときの規約)
- [6. 変更履歴](#6-変更履歴)

---

## 1. backend の責務

`backend/` は**「ジョブの受付・実行・進捗の配信」**を受け持つ。ただし `backend/` 自体は薄い Web 層で、
エージェントの中身の多くはリポジトリ直下の `grace/` などにある。
画面と操作は `frontend/` の担当で、frontend は判断も処理もしない
（frontend 側の役割表は [`frontend/docs/README.md` §1](../../frontend/docs/README.md#1-frontend-の責務)。2026-09-27 時点のコードから整理）。

**全体像**

```
ブラウザ ─ frontend/（Vite + React 18 + TypeScript, :5173）
             │  /api/* は Vite の proxy で :8000 へ転送（vite.config.ts）
             ▼
          backend/app/（FastAPI, :8000）── Web の入口・ジョブ管理・SSE 配信
             │  関数呼び出し
             ▼
          grace/・agent_tools.py・support_actions.py・chunking/・qa_generation/ …
             │                     （エージェント基盤・RAG・アクション・データ準備）
             ▼
          Anthropic（LLM）/ Gemini（Embedding）/ Qdrant（ベクトル DB）
```

**backend/ の役割（Web の入口とジョブの実行）**

| 場所 | 役割 |
|---|---|
| `app/main.py` | FastAPI の起動と 5 つのルーターの登録 |
| `app/api/support.py` | `POST /api/support/query` → 実行（`job_id` を返す）、`GET /stream/{id}` → SSE、`POST /confirm/{id}` → HITL 承認、`GET /result/{id}` |
| `app/api/review.py` | Review 用の同じ 4 本（`/api/review/submit` …） |
| `app/api/data.py`・`qdrant.py` | チャンク化 / Q&A 生成 / Qdrant 登録・削除のジョブ、コレクション一覧・詳細、入力ファイル一覧 |
| `app/api/meta.py` | 選べるモデル・業界プロファイル・ルールセット・ヘルスチェック |
| `app/schemas.py` | リクエスト・レスポンスの型（pydantic）。入力の検証もここで行う |
| `app/core/support_agent.py`・`review_agent.py` | 2 つのエージェントのパイプライン本体（① Plan → … → ⑥/⑦ Action） |
| `app/core/gates.py`・`review_gates.py`・`verticals.py`・`rulesets.py` | 回答ゲート・判定ルール・業界プロファイル・ルールセットの定義 |
| `app/core/jobs.py`・`data_jobs.py`・`intervention_bridge.py` | ジョブの管理と進捗イベントの発行、HITL 承認の待ち合わせ |

**持たないもの**: 画面の描画と入力の保持（`frontend/`）、エージェント基盤・RAG・アクション実行の実装本体
（`grace/`・`agent_tools.py`・`support_actions.py` など。`backend/app/core/` はこれらを呼び出して 1 周のパイプラインに組み立てる）。

**1 回の問い合わせの流れ**（GRACE-Support の例。詳細は [`job_runtime.md`](./job_runtime.md)・[`api_contract.md`](./api_contract.md)）

1. 画面で「送信」を押すと、frontend の `api/client.ts` が `POST /api/support/query` を送る。backend はすぐに `job_id` を返す（202）
2. 画面は `EventSource('/api/support/stream/{job_id}')` で購読を始める。backend は各ステップの開始・完了・ログを SSE で順に送り、ステップトレースが更新される
3. ⑥ Action で承認が必要になると、backend は承認待ちのイベントを送って止まる。画面は CONFIRM モーダルを出し、押されたボタンに応じて `POST /api/support/confirm/{job_id}` を送る
4. 完了のイベントで、回答カードが表示される

**分担のルール**（CLAUDE.md より）

- **スキーマは両側で合わせる**: `backend/app/schemas.py` を変えたら `frontend/src/types.ts` も直す。直さないと frontend の CI ゲート（tsc）でマージが止まる
- **入口は Web API だけ**: エージェントを動かす入口は backend の Web API だけで、CLI は無い。データ準備の CLI（`chunking/`・`qa_qdrant/`）は現役
- **判断を画面に書かない**（frontend 側の規約）: 画面側の判断ロジックは `frontend/src/state/` の純関数へ出す。backend が返す値（モデル名・業界プロファイル等）を frontend で読み替えない

---

## 2. 読む順路

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

## 3. 文書一覧

### 3.1 横断（backend 全体を理解する）

| 文書 | 種別 | 何が書いてあるか |
|---|:--:|---|
| [`architecture.md`](./architecture.md) | A | 層構造、17 モジュールの責務と行数、**backend が持たないもの（外部境界）**、依存の向き、リクエストが通る経路 |
| [`job_runtime.md`](./job_runtime.md) | A | **3 系統が共有する実行基盤の正本。** ジョブのライフサイクル、イベントのリプレイ、runner 注入、HITL の橋渡し、ログ転送、ローカル専用であることの制約 |
| [`api_contract.md`](./api_contract.md) | A | 全 23 エンドポイント、SSE のワイヤ形式、HTTP ステータスの使い分け、`frontend/src/types.ts` との対応 |
| [`config_and_providers.md`](./config_and_providers.md) | A | **モデル名の 3 本の解決経路**、`judge_model()` / `detect_model()`、API キーのガード位置 |
| [`pitfalls.md`](./pitfalls.md) | B | 非自明な設計判断・過去に壊れた箇所・**直してはいけないもの** |

### 3.2 系統別（何をどう判断しているか）

| 文書 | 種別 | 対象 |
|---|:--:|---|
| [`support_flow.md`](./support_flow.md) | A | GRACE-Support の処理フロー（0-(A)〜⑥）と設計判断。**WHY と HOW が 1 本**（v3.0 で `support_spec.md` を統合） |
| [`review_flow.md`](./review_flow.md) | A | GRACE-Review の処理フロー（S1・①〜⑦）と設計判断（v2.0 で `review_spec.md` を統合） |
| [`verticals_and_rulesets.md`](./verticals_and_rulesets.md) | A | 業界プロファイル（gov / saas / ec）とルールセット（ec_ad）の**カタログ**・増やし方 |
| [`data_pipeline.md`](./data_pipeline.md) | A | チャンク化 → Q/A 生成 → Qdrant 登録（付録A: 規程コレクションの準備） |
| [`webapp_flow.md`](./webapp_flow.md) | A | `run_dev.sh` 起点の end-to-end（ブラウザ → FastAPI → コア → 描画） |

### 3.3 モジュール参照（`reference/`）— 引く用

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

### 3.4 運用・記録

| 文書 | 種別 | 内容 |
|---|:--:|---|
| [`install_and_setup.md`](./install_and_setup.md) | B | 環境構築・**起動手順の正本** |
| [`testing.md`](./testing.md) | B | `backend/tests` の地図・結合テスト（実 Qdrant / Redis）・E2E（実 API・実データ）・どこを触ったらどれを流すか・CI の 4 ゲート |
| [`migration_plan.md`](./migration_plan.md) | C | 文書再編の計画（Phase 1 完了 / Phase 2・3 の予定） |
| [`docs_audit.md`](./docs_audit.md) | C | 棚卸し・実装追随の照合結果・検証スクリプト・残タスク |
| [`archive/`](./archive/) | — | 記録としては残すが実装の正ではない文書 |

---

## 4. 目的別の早見表

| やりたいこと | 読む文書 |
|---|---|
| backend の全体像を掴む | `architecture.md` |
| SSE / ジョブ / HITL の仕組みを知る | `job_runtime.md` |
| 新しいエンドポイントを足す | `api_contract.md` → `job_runtime.md` §3 → `reference/api_*.md` |
| 新しいジョブ種別を足す | `job_runtime.md` §3・§8 → `reference/core_data_jobs.md` |
| 回答が escalate に倒れる理由を追う | `support_flow.md` → `reference/core_gates.md` |
| 指摘が出ない / 誤検知する理由を追う | `review_flow.md` → `reference/core_review_gates.md` |
| 業界プロファイル / ルールセットを増やす | `verticals_and_rulesets.md` §3 |
| テストを足す・どれを流すか調べる・E2E を走らせる | `testing.md` |
| 既定モデルを変える | `config_and_providers.md` §6 |
| 起動できない・キーが無い | `install_and_setup.md` → `config_and_providers.md` §4 |
| 触る前に地雷を確認する | `pitfalls.md` |

---

## 5. 文書を書くときの規約

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

## 6. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 2.7 | 2026-10-08 | 軽量モデルを Haiku 4.5（`claude-haiku-4-5` / `claude-haiku-4-5-20251001`）から Claude Haiku 5.5（`claude-haiku-5-5`）へ変更したのに追随 |
| 2.6 | 2026-09-27 | **§1「backend の責務」を新設**し、frontend / backend の役割分担の要約（全体像の図・backend の役割表・持たないもの・1 回の問い合わせの流れ・分担のルール）を置いた。frontend 側の同じ要約（`frontend/docs/README.md` §1 v2.8）と対になる。これに伴い既存の §1〜§5 を §2〜§6 へ繰り下げた（本書内・他文書から本書の節番号を参照している箇所は無いことを grep で確認） |
| 2.5 | 2026-09-26 | Embedding を `gemini-embedding-001` に戻したのに追随（2026-09-26。同日に一度 `gemini-embedding-2` へ変えたが、既存の Qdrant コレクションと grace_v2_local（同じ Qdrant を共用）をそのまま使うため戻した。定義は `config.py::ModelConfig.EMBEDDING_MODEL`） |
| 2.4 | 2026-09-26 | 現在の Embedding の記述を `gemini-embedding-001` から `gemini-embedding-2` へ是正（2026-09-26 に変更。定義は `config.py::ModelConfig.EMBEDDING_MODEL` の 1 箇所） |
| 2.3 | 2026-09-24 | `a_cross_doc_md_format.md` v1.1（種別 C）に準拠（2026-09-24）。目次を追加し、§2 の各表へ「種別」列（A / B / C、`reference/` は E）を足し、§4 の規約表に横断文書フォーマットを追加した |
| 2.2 | 2026-09-16 | **Phase 3 を反映**。`reference/` の 17 文書に位置づけヘッダーが付いたことを §2.3 に明記した（圧縮は実測の結果不要と判断。[`migration_plan.md` §4](./migration_plan.md)） |
| 2.1 | 2026-09-16 | **Phase 2 を反映**。`support_spec.md` / `review_spec.md` を各 `*_flow.md` へ統合し、`verticals_and_rulesets.md` と `testing.md` を新設した（[`migration_plan.md` §3](./migration_plan.md)） |
| 2.0 | 2026-09-16 | 棚卸し内容を `docs_audit.md` へ分離し、README を**地図**に作り替えた。モジュール文書 17 本を `reference/` へ移動し、横断文書 5 本を新設した |
| 1.11 以前 | 〜2026-09-15 | [`docs_audit.md`](./docs_audit.md) の変更履歴を参照 |
