# backend アーキテクチャ ドキュメント

**Version 1.0** | 最終更新: 2026-09-16

> **本書の位置づけ**: `backend/` を理解するときに**最初に読む 1 枚**。
> 層構造・モジュールの責務・外側のパッケージとの境界・依存の向きを示す。
> 個々の段の判断ロジックは系統別文書（`support_flow.md` / `review_flow.md` /
> `data_pipeline.md`）、共有基盤は [`job_runtime.md`](./job_runtime.md) に分ける。

> **関連ドキュメント**
> - [`job_runtime.md`](./job_runtime.md) — ジョブ・SSE・HITL の共有基盤（本書の次に読む）
> - [`api_contract.md`](./api_contract.md) — エンドポイント一覧と SSE のワイヤ形式
> - [`config_and_providers.md`](./config_and_providers.md) — モデル・API キーの解決経路
> - [`pitfalls.md`](./pitfalls.md) — 触る前に知っておく落とし穴

---

## 目次

- [概要](#概要)
- [1. 層構造](#1-層構造)
- [2. モジュール一覧](#2-モジュール一覧)
- [3. 3 系統 × 1 共有基盤](#3-3-系統--1-共有基盤)
- [4. backend が持たないもの（外部境界）](#4-backend-が持たないもの外部境界)
- [5. 依存の向き](#5-依存の向き)
- [6. リクエストが通る経路（Support の例）](#6-リクエストが通る経路support-の例)
- [7. 読む順路](#7-読む順路)
- [8. 変更履歴](#8-変更履歴)

---

## 概要

`backend/app/` は **FastAPI の薄い層**である。17 モジュール・約 7,400 行のうち、
API 層（`api/*.py` + `main.py`）は合計 724 行しかなく、やっていることは

1. Pydantic でリクエストを検証し、
2. ジョブを起動し（`core/jobs.py`）、
3. 進捗を SSE に変換して流す

の 3 つだけである。**実処理は `backend/` の外**（`grace/` の planner / executor /
confidence / intervention、`services/`、`chunking/` `qa_generation/` `qa_qdrant/`、
`support_actions.py`）にある。

`backend/app/core/` が担うのは、その外側の部品を**業務手順として組み立てる**ことと、
**判断（ゲート）**である。行数の上位が `gates.py`（1,367 行）・`review_agent.py`
（1,093 行）・`data_jobs.py`（767 行）であることが、そのまま
「backend の難所は API ではなく判定ロジックである」ことを示している。

---

## 1. 層構造

```mermaid
flowchart TB
    subgraph Client["クライアント"]
        FE["frontend/ (Vite + React + TS)"]
    end
    subgraph Api["backend/app/api/ - HTTP 境界 (724行)"]
        ApiSupport["support.py"]
        ApiReview["review.py"]
        ApiData["data.py"]
        ApiQdrant["qdrant.py"]
        ApiMeta["meta.py"]
    end
    subgraph Core["backend/app/core/ - 組み立てと判断 (6,186行)"]
        Runtime["jobs.py / intervention_bridge.py / job_logs.py"]
        SupportCore["support_agent.py + gates.py + verticals.py"]
        ReviewCore["review_agent.py + review_gates.py + rulesets.py"]
        DataCore["data_jobs.py"]
    end
    subgraph Outside["backend の外 - 実処理"]
        Grace["grace/ (planner/executor/confidence/intervention/tools)"]
        Services["services/ (qdrant_service / data_pipeline_service)"]
        Actions["support_actions.py (ActionBackend)"]
        Pipes["chunking/ qa_generation/ qa_qdrant/"]
    end
    FE --> ApiSupport
    FE --> ApiReview
    FE --> ApiData
    FE --> ApiQdrant
    FE --> ApiMeta
    CLI --> SupportCore
    ApiSupport --> Runtime
    ApiReview --> Runtime
    ApiData --> Runtime
    ApiQdrant --> Services
    ApiMeta --> SupportCore
    Runtime --> SupportCore
    Runtime --> ReviewCore
    Runtime --> DataCore
    SupportCore --> Grace
    SupportCore --> Actions
    ReviewCore --> Grace
    ReviewCore --> Actions
    DataCore --> Pipes
    DataCore --> Services
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class FE,CLI,ApiSupport,ApiReview,ApiData,ApiQdrant,ApiMeta,Runtime,SupportCore,ReviewCore,DataCore,Grace,Services,Actions,Pipes default
style Client fill:#1a1a1a,stroke:#fff,color:#fff
style Api fill:#1a1a1a,stroke:#fff,color:#fff
style Core fill:#1a1a1a,stroke:#fff,color:#fff
style Outside fill:#1a1a1a,stroke:#fff,color:#fff
```

> ⚠️ **エージェント実行の CLI 入口は無い（2026-09-19 以降）。** Support / Review とも
> Web API 専用である。かつて Support には `agent_support_example.py` があり
> `run_support_agent_core` を直接呼んでいたが、機能確認用の薄いラッパだったため削除した。
> データ準備は `chunking/` 等の**パッケージ側**に別の CLI がある（こちらは現役）。

---

## 2. モジュール一覧

行数は 2026-09-16 の `wc -l` 実測値。

### 2.1 API 層（`backend/app/`）

| モジュール | 行数 | 責務 | prefix |
|---|---:|---|---|
| `main.py` | 66 | FastAPI 組み立て・CORS・ルータ登録・`.env` 読み込み | — |
| `schemas.py` | 462 | 全リクエスト / レスポンス / イベントの Pydantic モデル | — |
| `api/support.py` | 89 | Support のジョブ起動 / SSE / HITL 応答 / 結果取得 | `/api/support` |
| `api/review.py` | 104 | Review の同上（構造は support.py と同一） | `/api/review` |
| `api/data.py` | 197 | データ準備 4 ジョブの起動 + 共通 SSE / HITL / 結果 | `/api` |
| `api/qdrant.py` | 200 | Qdrant 参照系（読み取り専用）・入力ファイル一覧 | `/api` |
| `api/meta.py` | 68 | 業界プロファイル / ルールセット一覧・ヘルスチェック | `/api` |

### 2.2 core 層（`backend/app/core/`）

| モジュール | 行数 | 系統 | 責務 |
|---|---:|---|---|
| `jobs.py` | 302 | 共有 | ジョブ管理・runner 注入・イベント蓄積とリプレイ |
| `intervention_bridge.py` | 139 | 共有 | HITL の同期コールバック ↔ 非同期 API の橋渡し |
| `job_logs.py` | 193 | 共有 | 既存パッケージの `logging` を進捗イベントへ転送 |
| `support_agent.py` | 916 | Support | `run_support_agent_core`（0-(A)〜⑥ の 1 周） |
| `gates.py` | 1,367 | Support | 質問分析・回答ゲート・救済・スコープ判定・情報なし検知 |
| `verticals.py` | 256 | Support | `VerticalProfile`（gov / saas / ec） |
| `review_agent.py` | 1,093 | Review | `run_review_agent_core`（S1・①〜⑦ の 1 周） |
| `review_gates.py` | 510 | Review | 二段判定・誤検知抑止・救済・重大度調整 |
| `rulesets.py` | 643 | Review | `RuleSet` / `RuleItem`（EC 広告 23 ルール） |
| `data_jobs.py` | 767 | データ準備 | 4 種の runner（chunking / qa / register / delete） |

---

## 3. 3 系統 × 1 共有基盤

backend には**性格の違う 3 系統**が載っているが、実行基盤は 1 つを共有する。

| | GRACE-Support | GRACE-Review | データ準備 |
|---|---|---|---|
| 情報の流れ | 問い合わせ → 回答 | 文書 → 指摘 | ファイル → Qdrant |
| 起動 | `POST /api/support/query` | `POST /api/review/submit` | `POST /api/chunking/run` ほか 3 種 |
| params 型 | `JobParams` | `ReviewParams` | `ChunkingParams` ほか 3 種 |
| 結果型 | `SupportResultModel` | `ReviewResultModel` | `DataJobStatusResponse` |
| ステップ | `STEP_IDS`（9 段） | `REVIEW_STEP_IDS`（9 段） | 種別ごとに 3〜4 段 |
| HITL CONFIRM | ⑥ Action で条件付き | ⑦ Action で条件付き | 削除は常に / 登録は `recreate` 時のみ |
| **ジョブ基盤・SSE・HITL** | **共通（`core/jobs.py`）** | **共通** | **共通** |

`api/review.py` と `api/data.py` の docstring が自ら
「`api/support.py` と**構造は同一**」と書いているとおり、3 系統の API 実装は
**params 型と結果型以外は同じ**である。したがって

- **共通部の説明は [`job_runtime.md`](./job_runtime.md) に一本化する**
- 系統別文書は「この系統に固有な params / 結果 / ステップ / CONFIRM の要否」だけを書く

という分担にする。これは `jobs.py` が runner 注入で汎用化されているという
**実装の構造をそのまま写した**もので、文書の重複が構造的に発生しない。

---

## 4. backend が持たないもの（外部境界）

`backend/app/` が import している**リポジトリ内の外部モジュール**は以下がすべてである
（標準ライブラリ・FastAPI・Pydantic を除く）。

| 外部モジュール | 使う側 | 何を委ねているか |
|---|---|---|
| `grace`（`create_intervention_handler` / `create_tool_registry` / `get_config`） | `support_agent.py` / `review_agent.py` | エージェント基盤の生成・設定解決 |
| `grace.confidence.create_groundedness_verifier` | `support_agent.py` / `review_agent.py` | ③④ 根拠検証（**Support / Review 共用**） |
| `grace.intervention`（`InterventionRequest` / `InterventionResponse` / `InterventionAction`） | `intervention_bridge.py` | HITL の型とアクション |
| `grace.llm_compat.create_chat_client` | `gates.py` / `review_gates.py` | 判定系の LLM 呼び出し |
| `support_actions`（`create_action_backend` / `create_identity_verifier`） | `support_agent.py` / `review_agent.py` | ⑥⑦ アクション実行・本人確認（**共用**） |
| `services.qdrant_service`（`QdrantHealthChecker` / `QdrantDataFetcher` / `get_all_collections`） | `api/qdrant.py` | Qdrant の参照 |
| `services.data_pipeline_service` | `api/qdrant.py` / `data_jobs.py` | 入力ファイル解決・コレクション操作 |
| `chunking.csv_text_to_chunks_text_csv` / `chunking.async_api_client` | `data_jobs.py` | チャンク化本体 |
| `qa_qdrant.register_to_qdrant` | `data_jobs.py` | Qdrant 登録本体 |
| `qdrant_client_wrapper.get_qdrant_client` | `api/qdrant.py` | Qdrant クライアント生成 |
| `config.ModelConfig` | `data_jobs.py` | チャンク化・Q/A 生成の既定モデル |

**この表の裏返しが「backend を読むだけでは分からないこと」**である。
RAG 検索の実装・planner のプロンプト・Qdrant への upsert 手順などを追うときは、
`grace/docs/` `services/docs/` `chunking/docs/` 側の文書へ移る。

> ⚠️ **共用部品は Support と Review の両方に効く。** `GroundednessVerifier` /
> `InterventionBridge` / `support_actions.py` を触った変更は、Support のつもりでも
> Review を壊す。`backend/tests` の約 1/3（18 ファイル）が Review 系である。

---

## 5. 依存の向き

守られている規律は 3 つ。**ここを崩すと循環 import になる。**

1. **`core/` は `api/` を知らない。** 逆向きの import は存在しない。
2. **`jobs.py` は Review・データ準備を知らない。**
   Support の runner だけを自分で登録し、Review / データ準備の runner は
   `review_agent.py` / `data_jobs.py` が**自分の import 時に**
   `register_runner()` で登録する（[`job_runtime.md` §3](./job_runtime.md)）。
3. **判定ロジックは `*_gates.py` に集める。**
   `review_gates.py` は `gates.py` から `_match_keyword` / `judge_model` を再利用する
   （Review → Support の一方向）。

```mermaid
flowchart LR
    ApiLayer["api/*.py"] --> JobsMod["core/jobs.py"]
    ApiLayer --> CoreAgents["core/*_agent.py"]
    JobsMod --> SupportAgent["core/support_agent.py"]
    ReviewAgent["core/review_agent.py"] -->|register_runner| JobsMod
    DataJobs["core/data_jobs.py"] -->|register_runner| JobsMod
    SupportAgent --> Gates["core/gates.py"]
    ReviewAgent --> ReviewGates["core/review_gates.py"]
    ReviewGates -->|_match_keyword / judge_model| Gates
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class ApiLayer,JobsMod,CoreAgents,SupportAgent,ReviewAgent,DataJobs,Gates,ReviewGates default
```

---

## 6. リクエストが通る経路（Support の例）

```mermaid
%%{ init: { "theme": "base", "themeVariables": {
  "background": "#000000", "mainBkg": "#000000",
  "textColor": "#ffffff", "lineColor": "#ffffff",
  "actorBkg": "#000000", "actorTextColor": "#ffffff",
  "actorLineColor": "#ffffff", "noteBkgColor": "#000000",
  "noteTextColor": "#ffffff", "noteBorderColor": "#ffffff" } } }%%
sequenceDiagram
    participant FE as "frontend"
    participant API as "api/support.py"
    participant JM as "JobManager"
    participant W as "ワーカースレッド"
    participant CORE as "run_support_agent_core"
    FE->>API: POST /api/support/query
    API->>JM: start(JobParams(...))
    JM->>W: Thread(runner, emit, confirm)
    API-->>FE: 202 {job_id, stream_url}
    FE->>API: GET /api/support/stream/{job_id}
    W->>CORE: 実行開始
    CORE-->>JM: emit(SupportEvent) x N
    JM-->>FE: SSE data: {...}
    CORE->>JM: confirm(InterventionRequest)
    JM-->>FE: SSE intervention (waiting)
    FE->>API: POST /api/support/confirm/{job_id}
    API->>JM: resolve(approve)
    JM-->>CORE: InterventionResponse
    CORE-->>JM: 最終結果
    JM-->>FE: SSE done (番兵)
```

> 📎 上図は **backend の中だけ**を描いている。ブラウザの描画まで含めた end-to-end は
> [`webapp_flow.md` §6](./webapp_flow.md#6-リクエストライフサイクルシーケンス図) にある
> （同じ流れを、フロントと `grace/` を加えた粒度で示したもの）。

**ポイント**: HTTP 応答は 202 で即返り、実体はワーカースレッドで走る。
HITL は「SSE で聞き、別の POST で答える」という**2 本の HTTP を跨ぐ**やり取りになる。
この橋渡しが `InterventionBridge` である（[`job_runtime.md` §4](./job_runtime.md)）。

Review・データ準備も**まったく同じ形**で、違うのは params 型・結果型・
CONFIRM を出す条件だけである。

---

## 7. 読む順路

```
architecture.md（本書）
  └ job_runtime.md          ジョブ・SSE・HITL の共有基盤（必読）
      ├ support_flow.md     担当する系統だけ読む
      ├ review_flow.md
      └ data_pipeline.md
api_contract.md             フロント / API 利用者はここから
config_and_providers.md     モデル・キーを触る前に
pitfalls.md                 コードを触る前に
reference/*.md              引く（通読しない）
```

---

## 8. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-16 | 新規作成。層構造・モジュール一覧・外部境界・依存の向きを実装から書き起こした |
