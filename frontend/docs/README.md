# frontend — 責務・構成・モジュール構造

**Version 2.5** | 最終更新: 2026-09-26

`frontend/`（Vite + React 18 + TypeScript）の**入口文書**である。
前半（§1〜§7）で frontend の責務・構成・モジュール構造・データの流れを説明し、
後半（§8〜§13）で文書一覧・実装カバレッジ・テスト件数などの**棚卸し**を持つ。

> **新しいコンポーネント / `state/` モジュールを足したら、同じコミットで本書の表にも行を足すこと**
> （索引が無かった頃、コンポーネント 4 件の文書欠落が長期間検知されずに残っていた）。

> **関連**: 形式仕様は [`.claude/skills/grace-agent-docs/a_react_page_md_format.md`](../../.claude/skills/grace-agent-docs/a_react_page_md_format.md) ／
> 純関数規約は CLAUDE.md §6 ／ 姉妹リポジトリ（grace_v2_local）との乖離は CLAUDE.md §5 ／
> [`grace/docs/README.md`](../../grace/docs/README.md) ／ [`backend/docs/README.md`](../../backend/docs/README.md) ／
> 全体の改修計画は [`docs/doc_modernization_todo.md`](../../docs/doc_modernization_todo.md)

---

## 目次

- [1. frontend の責務](#1-frontend-の責務)
- [2. 技術スタックとビルド構成](#2-技術スタックとビルド構成)
- [3. ディレクトリ構成](#3-ディレクトリ構成)
- [4. レイヤー構造と依存の向き](#4-レイヤー構造と依存の向き)
- [5. 画面構成（コンポーネントツリー）](#5-画面構成コンポーネントツリー)
- [6. バックエンドとの通信](#6-バックエンドとの通信)
- [7. 状態管理の設計方針](#7-状態管理の設計方針)
- [8. 文書一覧](#8-文書一覧)
- [9. 実装カバレッジ](#9-実装カバレッジ)
- [10. state/ 純関数の一覧](#10-state-純関数の一覧)
- [11. テスト件数（実測）](#11-テスト件数実測)
- [12. 検証手順](#12-検証手順)
- [13. 既知の問題・残タスク](#13-既知の問題残タスク)
- [14. 変更履歴](#14-変更履歴)

---

## 1. frontend の責務

GRACE のローカル開発用 Web UI。**唯一のエージェント実行入口**である Web API
（`backend/app/`・FastAPI :8000）を画面から操作する（CLI 入口は 2026-09-19 に削除済み。CLAUDE.md §1）。

### 1.1 やること

| 責務 | 内容 |
|---|---|
| **エージェントの実行と可視化** | 問い合わせ / 文書を送り、SSE で届くステップ進捗をタイムラインとして逐次表示し、最終結果（回答カード / 指摘一覧）を描画する |
| **HITL（Human-In-The-Loop）の窓口** | バックエンドから届く承認待ち（`intervention`）に対し、承認 / 拒否（⑥ アクション・データ削除・`recreate`）や主質問の選択（0-(A)）を利用者に求め、結果を POST で返す |
| **データ準備の操作** | チャンキング → Q/A 作成 → Qdrant 登録 → コレクション管理を、CLI と同じ関数経由で画面から実行する |
| **実行条件の選択** | モデル（ヘッダー・**単価つき**）・業界プロファイル / ルールセット・Web フォールバック・アクション実行・dry-run・詳細ログを選ぶ |
| **アクセシビリティ** | tablist の矢印キー移動、モーダルのフォーカストラップ、指摘選択のキーボード操作、`aria-live` による進捗の読み上げ、banner 系への `role` 付与、IME 変換中は送信しない等 |

### 1.2 やらないこと（バックエンドの責務）

| やらないこと | 実際の持ち主 |
|---|---|
| LLM（Anthropic Claude）呼び出し・RAG 検索・根拠検証（groundedness）・ゲート判定 | `backend/app/core/support_agent.py` / `review_agent.py`、`grace/` |
| アクションの実行・安全側への倒し方（承認タイムアウト時は実行しない） | `support_actions.py`（`ActionBackend`）・`InterventionBridge` |
| 業界プロファイル / ルールセットの定義 | `backend/app/core/verticals.py` / `rulesets.py`（frontend は `GET` で取得して選ばせるだけ） |
| モデル名・単価・選択肢の決定 | `config.py::ModelConfig`（`SELECTABLE_MODELS` / `MODEL_PRICING` / Embedding は `EMBEDDING_MODEL`）。frontend は `GET /api/model` / `GET /api/models` が返した値をそのまま出す。**既定モデル名を frontend に書かない・モデル名を変換しない**（`state/modelLabel.ts` 冒頭・CLAUDE.md R1） |
| 永続化 | 無し。frontend はブラウザストレージも使わない（§7.4） |

> frontend は **「決める」のではなく「見せて、選ばせて、返す」** 層である。
> 判断が必要な箇所（送信ペイロードの組み立て・表示文言・キー操作）は
> すべて `state/` の純関数へ出してテスト可能にしている（§7.1）。

---

## 2. 技術スタックとビルド構成

| 項目 | 内容 |
|---|---|
| ランタイム依存 | **`react` / `react-dom` の 2 つだけ**（ルータ・状態管理ライブラリ・Markdown ライブラリ・CSS フレームワークは使わない） |
| 開発依存 | `typescript` 5.6 / `vite` 5.4 / `@vitejs/plugin-react` / `vitest` 2.1 / `@types/react*` |
| 型設定 | `tsconfig.json` — `strict` / `noUnusedLocals` / `noUnusedParameters` / `jsx: react-jsx` / `noEmit` |
| dev サーバ | `vite`（:5173）。**`/api` を `http://127.0.0.1:8000` へプロキシ**（SSE も同経路） |
| テスト | vitest。`environment: 'node'`・`include: ['src/**/*.test.ts']`（**`.test.tsx` は収集されない**・DOM なし） |
| スタイル | `src/styles.css`（1,342 行）1 枚のグローバル CSS |
| エントリ | `index.html`（`lang="ja"`）→ `src/main.tsx` → `<App />`（`React.StrictMode`） |

> ⚠️ **プロキシ先は `localhost` ではなく `127.0.0.1`。** Node 18+ は `localhost` を
> IPv6（`::1`）優先で解決し、IPv4 のみに bind する uvicorn へ繋がらず `/api/*` が全滅する
> （`vite.config.ts` のコメント参照）。

### npm scripts

| script | 実体 | 用途 |
|---|---|---|
| `dev` | `vite` | 開発サーバ（通常は `./run_dev.sh` から backend と同時起動） |
| `lint` | `tsc --noEmit` | 型検査（CI ゲート） |
| `test` | `vitest run` | 単体テスト（CI ゲート） |
| `build` | `tsc --noEmit && vite build` | 本番ビルド（CI ゲート） |
| `preview` | `vite preview` | ビルド結果の確認 |

---

## 3. ディレクトリ構成

```
frontend/
├── index.html                # <div id="root"> と main.tsx の読み込みだけ
├── package.json / tsconfig.json / vite.config.ts
├── docs/                     # 本書 + <Component>.md（§8）
└── src/
    ├── main.tsx              # ReactDOM.createRoot → <App/>（10 行）
    ├── App.tsx               # 4 タブの切替・ヘッダーのモデル選択（169 行）
    ├── types.ts              # API スキーマの型（backend/app/schemas.py と 1:1・431 行）
    ├── styles.css            # グローバル CSS（1,342 行）
    ├── api/
    │   └── client.ts         # fetch / EventSource を包む唯一の通信層（301 行）
    ├── components/           # 19 コンポーネント（.tsx）+ ReviewForm の例文テスト
    ├── state/                # 判断ロジックの純関数・reducer・ストア（21 モジュール）+ テスト
    └── markdown/
        └── parseMarkdown.ts  # 依存なしの Markdown → ブロック AST（250 行）+ テスト
```

| ディレクトリ | 置いてよいもの | 置いてはいけないもの |
|---|---|---|
| `api/` | HTTP / SSE の呼び出し、エラーの `Error` 化 | 画面の状態・判断 |
| `components/` | 入力の保持（`useState`）・副作用（`useEffect`）・描画 | **判断ロジック**（→ `state/`） |
| `state/` | 純関数・reducer・モジュールスコープのストア | JSX・React の型への直接依存（`useJobTiming.ts` のみ例外。§10） |
| `markdown/` | 回答本文の Markdown パーサ（純関数） | React 要素の生成（→ `components/Markdown.tsx`） |
| `types.ts` | バックエンドのスキーマ写し | frontend 独自の UI 状態型（→ 各 `state/*.ts`） |

---

## 4. レイヤー構造と依存の向き

依存は**上から下への一方向**である。`state/` と `markdown/` は React にも `api/` にも依存しないので、
node 環境の vitest からそのまま呼べる。

```mermaid
flowchart TB
    subgraph Entry["エントリ"]
        Main["main.tsx"]
        AppNode["App.tsx（タブ・ヘッダーのモデル選択）"]
    end
    subgraph Containers["コンテナ（状態・副作用・API を束ねる）"]
        Support["SupportPanel"]
        Review["ReviewPanel"]
        Data["DataPanel"]
        DataJob["DataJobPanel"]
        Collection["CollectionPanel"]
    end
    subgraph Presentational["入力・表示・モーダル"]
        Forms["QueryForm / ReviewForm"]
        Modals["ConfirmModal / QuestionSelectModal"]
        Views["AnswerCard / FindingList / DocumentView / Markdown"]
        Timelines["StepTimeline / ReviewTimeline / Timeline"]
        Misc["JobClock / MetaErrorBanner"]
    end
    subgraph Logic["判断ロジック（React 非依存）"]
        StateMod["state/ 純関数・reducer・ストア"]
        MdParse["markdown/parseMarkdown.ts"]
    end
    subgraph IO["通信・型"]
        Client["api/client.ts"]
        Types["types.ts"]
    end
    Backend["FastAPI :8000（/api/*）"]

    Main --> AppNode
    AppNode --> Support
    AppNode --> Review
    AppNode --> Data
    Data --> DataJob
    Data --> Collection
    Support --> Forms
    Review --> Forms
    Support --> Modals
    Review --> Modals
    DataJob --> Modals
    Collection --> Modals
    Support --> Views
    Review --> Views
    Support --> Timelines
    Review --> Timelines
    DataJob --> Timelines
    Collection --> Timelines
    Support --> Misc
    Review --> Misc
    Containers --> Client
    AppNode --> Client
    Containers --> StateMod
    Presentational --> StateMod
    Views --> MdParse
    Client --> Types
    StateMod --> Types
    Client -->|"fetch / EventSource（Vite プロキシ経由）"| Backend
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class Main,AppNode,Support,Review,Data,DataJob,Collection,Forms,Modals,Views,Timelines,Misc,StateMod,MdParse,Client,Types,Backend default
style Entry fill:#1a1a1a,stroke:#fff,color:#fff
style Containers fill:#1a1a1a,stroke:#fff,color:#fff
style Presentational fill:#1a1a1a,stroke:#fff,color:#fff
style Logic fill:#1a1a1a,stroke:#fff,color:#fff
style IO fill:#1a1a1a,stroke:#fff,color:#fff
```

| 層 | 実体 | `api/client.ts` を呼ぶか |
|---|---|:--:|
| エントリ | `main.tsx` / `App.tsx` | ✅（`fetchModelInfo` / `fetchModels` のみ） |
| コンテナ | `SupportPanel` / `ReviewPanel` / `DataJobPanel` / `CollectionPanel`（`DataPanel` はサブタブの枠のみ） | ✅ |
| 入力・表示・モーダル | 上記以外の 14 コンポーネント | ❌（props で受け取るだけ） |
| 判断ロジック | `state/*` / `markdown/parseMarkdown.ts` | ❌ |
| 通信・型 | `api/client.ts` / `types.ts` | — |

> **API を呼ぶのはコンテナと `App` だけ**である。表示コンポーネントに `fetch` を足さないこと
> （テストできない副作用が末端に散る）。

---

## 5. 画面構成（コンポーネントツリー）

### 5.1 タブ

`App.tsx` が 4 タブを**条件レンダリング（アンマウント方式）**で切り替える。

| タブ id | ラベル | 描画するコンテナ | 通信先 |
|---|---|---|---|
| `basic` | 基本版 | `SupportPanel variant="basic"`（業界プロファイルのセレクタを出さない・`vertical` は常に null） | `/api/support/*` |
| `support` | GRACE-Support | `SupportPanel variant="vertical"`（`gov` / `saas` / `ec` を選ぶ） | `/api/support/*` |
| `review` | GRACE-Review | `ReviewPanel` | `/api/review/*` |
| `data` | データ管理 | `DataPanel`（サブタブ ①〜④） | `/api/chunking` `/api/qa` `/api/qdrant` `/api/data` `/api/files` |

`basic` と `support` は**同じ `SupportPanel`** に `variant` と `key={tab}` を渡しているだけで、
別コンポーネントではない（`key` によりタブ切替で状態が混ざらない）。

### 5.2 ヘッダーのモデル選択

モデルは**ヘッダー（タイトル横）で選ぶ**（2026-09-23 にフォーム内セレクタ `ModelSelect` から移設・同日削除）。
選択は `App` の state にスロットごとに持つので、タブを切り替えても残る。

| タブ | スロット | 既定値の出どころ（`ModelInfo`） | パネルへの渡し方 |
|---|---|---|---|
| 基本版 / GRACE-Support / GRACE-Review | `basic` / `support` / `review`（1 つずつ） | `model` | `model` prop |
| データ管理 | `chunking` / `qa`（工程ごとに 2 つ） | `chunking_model` / `qa_model` | `chunkingModel` / `qaModel` prop |

- 空文字は「サーバーの既定値」を意味し、送信時に null 化される（`state/queryParams.ts` / `dataParams.ts`）。
- 選択肢は `GET /api/models`（= `config.py::ModelConfig.SELECTABLE_MODELS`）。ラベルは
  `state/modelLabel.ts::modelOptionLabel` が **入力 / 出力単価（$/1K tokens）つき**で組み立てる。
- エージェントのタブでは、論理層だけ別モデル（`llm.heavy_model`）へ寄せているとき
  `（論理層: …）` の注記を出す（`state/headerModel.ts::heavyModelNote`）。
- 並べ方・表示値・選択肢の組み立ては `state/headerModel.ts`。

> ⚠️ `modelLabel.ts` / `headerModel.ts` は **grace_v2_local の同名ファイルとは中身が別物**
> （あちらは Ollama の `supports_tool_calls` / `notes` を畳み込み、データ管理タブの既定値に
> `ModelInfo.model` を使う）。コピーで行き来させないこと（CLAUDE.md §5）。

### 5.3 ツリー

```
App
├── header: モデルセレクタ（スロット 1〜2 個・単価つき）＋ tablist
└── tabpanel
    ├── SupportPanel（basic / vertical）
    │   ├── MetaErrorBanner        業界プロファイル取得失敗
    │   ├── QueryForm              問い合わせ・オプション
    │   ├── JobClock（開始行）
    │   ├── StepTimeline → Timeline
    │   ├── AnswerCard → Markdown, JobClock（完了行）
    │   ├── ConfirmModal           ⑥ アクションの HITL 承認
    │   └── QuestionSelectModal    0-(A) 主質問の選択
    ├── ReviewPanel
    │   ├── MetaErrorBanner        ルールセット取得失敗
    │   ├── ReviewForm             文書 textarea・ルールセット・オプション
    │   ├── JobClock
    │   ├── ReviewTimeline → Timeline
    │   ├── DocumentView ⇄ FindingList   原文ハイライトと指摘カード（左右 2 ペイン・クリック / Enter / Space で相互ジャンプ）
    │   └── ConfirmModal           ⑦ アクションの HITL 承認
    └── DataPanel（サブタブ）
        ├── ① チャンキング   DataJobPanel variant=chunking
        ├── ② Q/A 作成      DataJobPanel variant=qa
        ├── ③ Qdrant 登録   DataJobPanel variant=register（recreate 時に ConfirmModal）
        │                     └── Timeline, JobClock, ConfirmModal
        └── ④ コレクション管理 CollectionPanel（削除は ConfirmModal を通すジョブ）
                              └── Timeline, JobClock, ConfirmModal
```

### 5.4 共用部品

| 部品 | 使う側 | 共用の理由 |
|---|---|---|
| `ConfirmModal` | Support / Review / DataJob / Collection の 4 か所 | HITL 承認の UI は 1 つに揃える（承認なしに不可逆操作をさせない）。フォーカストラップもここ 1 か所で全画面に効く |
| `Timeline` | `StepTimeline` / `ReviewTimeline` / `DataJobPanel` / `CollectionPanel` | マークアップと `aria-live` は共通、ステップ ID 集合とバッジは呼び出し側が渡す |
| `JobClock` | 4 つのコンテナ・`AnswerCard` | 開始 / 完了時刻と所要時間を同じ書式で出す |
| `MetaErrorBanner` | Support / Review | メタ取得失敗を無言で握りつぶさない |
| `state/formMemory.ts` | `QueryForm` / `ReviewForm` | アンマウントで入力が消えないよう退避 |
| `state/submitKey.ts` | `QueryForm` / `ReviewForm` | Ctrl+Enter / ⌘+Enter 送信・IME 変換中は送らない |
| `state/selectionKeys.ts` | `DocumentView` / `FindingList` | 指摘の選択を Enter / Space でも行い、トグル規則を 1 か所にそろえる |

---

## 6. バックエンドとの通信

### 6.1 通信方式

`api/client.ts` が**唯一の通信層**である。すべてのジョブは同じ 3 段で動く。

1. **POST でジョブ起動** → `job_id` を受け取る
2. **SSE（`EventSource`）で進捗を購読** — `subscribeStream(jobId, onEvent, onError, kind)` を 3 種（`support` / `review` / `data`）で共用
3. **承認待ちが来たら POST で応答**（`confirm*`）

SSE の 1 イベントは `types.ts::SupportEvent`（`type: 'step' | 'log' | 'intervention' | 'result' | 'error' | 'done'`）で、
**3 種のジョブで形式が同一**。`done` を受けると購読を閉じる。`done` 前の切断だけを
「バックエンドの起動を確認してください」というエラーとして通知する。
HTTP エラーは `requireOk()` が `API エラー (status): body` の `Error` に変換する。

```mermaid
%%{ init: { "theme": "base", "themeVariables": {
  "background": "#000000", "mainBkg": "#000000",
  "textColor": "#ffffff", "lineColor": "#ffffff",
  "actorBkg": "#000000", "actorTextColor": "#ffffff",
  "actorLineColor": "#ffffff", "noteBkgColor": "#000000",
  "noteTextColor": "#ffffff", "noteBorderColor": "#ffffff" } } }%%
sequenceDiagram
    participant U as "利用者"
    participant P as "コンテナ（SupportPanel 等）"
    participant R as "reducer（state/）"
    participant C as "api/client.ts"
    participant B as "FastAPI :8000"
    U->>P: 送信
    P->>C: startQuery(params)
    C->>B: POST /api/support/query
    B-->>C: job_id
    P->>C: subscribeStream(job_id)
    C->>B: GET /api/support/stream/job_id（SSE）
    loop ステップごと
        B-->>C: step / log イベント
        C-->>P: onEvent
        P->>R: dispatch → タイムライン更新
    end
    B-->>C: intervention イベント
    P->>U: ConfirmModal / QuestionSelectModal
    U->>P: 承認 / 拒否 / 選択
    P->>C: confirmIntervention(job_id, …)
    C->>B: POST /api/support/confirm/job_id
    B-->>C: result → done
    C-->>P: onEvent（done で購読を閉じる）
    P->>R: dispatch → 結果カード描画
```

### 6.2 エンドポイント一覧（`api/client.ts` の関数）

| 分類 | 関数 | メソッド・パス |
|---|---|---|
| Support | `startQuery` / `confirmIntervention` | `POST /api/support/query` / `POST /api/support/confirm/{job_id}` |
| Review | `startReview` / `confirmReviewIntervention` | `POST /api/review/submit` / `POST /api/review/confirm/{job_id}` |
| SSE（共用） | `subscribeStream` | `GET /api/{support\|review\|data}/stream/{job_id}` |
| メタ情報 | `fetchVerticals` / `fetchRuleSets` | `GET /api/verticals` / `GET /api/rulesets` |
| モデル | `fetchModelInfo` / `fetchModels` | `GET /api/model` / `GET /api/models` |
| Qdrant 参照 | `fetchQdrantHealth` / `fetchCollections` / `fetchCollectionDetail` / `fetchCollectionPoints` | `GET /api/qdrant/health` / `…/collections` / `…/collections/{name}` / `…/collections/{name}/points?limit=` |
| 入力ファイル | `fetchInputFiles` | `GET /api/files?dir=` |
| データ準備ジョブ | `startChunking` / `startQaGeneration` / `startRegister` / `startDelete` | `POST /api/chunking/run` / `POST /api/qa/generate` / `POST /api/qdrant/register` / `POST /api/qdrant/delete` |
| データ準備（共通） | `confirmDataIntervention` / `fetchDataJobStatus` | `POST /api/data/confirm/{job_id}` / `GET /api/data/result/{job_id}` |

> ⚠️ **バックエンドの API スキーマを変えたら `src/types.ts` も必ず追随させる。**
> Python 側が全部緑でも型エラー 1 個でマージは止まる（CLAUDE.md §4）。
> スキーマの正は [`backend/docs/reference/schemas.md`](../../backend/docs/reference/schemas.md)。

### 6.3 取得失敗時の方針

| 取得対象 | 失敗時 | 理由 |
|---|---|---|
| モデル情報・選択肢（`App`） | **握りつぶす**。既定モデルだけの選択肢に縮退 | サーバーは設定どおりのモデルで走るので機能は失われない |
| 業界プロファイル / ルールセット | **`MetaErrorBanner` で理由と再読み込みボタンを出す**（`state/metaFetch.ts`） | 空のセレクタだけでは「壊れている」としか見えないため |
| ジョブの起動・SSE 切断 | パネルのエラーバナー（`role` 付き） | 利用者が再実行を判断できるように |

---

## 7. 状態管理の設計方針

### 7.1 判断は `state/` の純関数へ（CLAUDE.md §6）

vitest は node 環境で `.test.ts` しか収集せず、`@testing-library/react` も未導入なので
**コンポーネントのレンダリングテストは書けない**。そのため:

- コンポーネントに残すのは**入力の保持と描画だけ**
- 「どう判断するか」（ペイロード組み立て・表示文言・キー判定・状態遷移）は `state/` の純関数へ出す
- React の型（`KeyboardEvent` 等）に直接依存させず、必要なフィールドだけのインターフェースを受ける

### 7.2 ジョブ状態は reducer 1 本ずつ

| reducer | 使うコンテナ | ステップ ID |
|---|---|---|
| `jobReducer.ts` | `SupportPanel` | 固定 9 個（`analyze` / `profile` / `plan` / `execute` / `confidence` / `gate` / `web` / `no_info` / `action`） |
| `reviewReducer.ts` | `ReviewPanel` | 固定（`REVIEW_STEP_IDS`・backend の `review_agent.py` と 1:1） |
| `dataReducer.ts` | `DataJobPanel` / `CollectionPanel` | **ジョブ種別で変わる**（`stepIdsFor(kind)` — chunking / qa / register / delete） |

3 つとも「SSE イベント列 → ステップ状態・承認待ち・最終結果」を畳み込む**同じ形**だが、
result の型が違うため**無理にジェネリック化しない**方針である（`reviewReducer.ts` 冒頭）。

### 7.3 タブはアンマウント方式 — 失うものと、その補い方

離れたタブの `EventSource` を `useEffect` のクリーンアップで確実に閉じるため、タブ（とデータ管理のサブタブ）は
**アンマウントで切り替える**。副作用として失われる状態は、コンポーネントより長生きする
**モジュールスコープのストア**で補っている。

| 失われるもの | 補うモジュール | 保持するもの |
|---|---|---|
| フォームの入力（`useState`） | `state/formMemory.ts` | `QueryForm` / `ReviewForm` の入力（**モデルは含まない** — ヘッダー側が持つ） |
| 実行中ジョブの `job_id` | `state/activeJobs.ts` | データ準備ジョブの `job_id`。再マウント時に SSE を購読し直し、承認待ちを見失わない |
| モデルの選択 | `App` の state（`headerModel.ts`） | スロットごとの選択。`App` はアンマウントされない |

### 7.4 ブラウザストレージは使わない

`formMemory` / `activeJobs` はどちらも**メモリ上のみ**で、`localStorage` / `sessionStorage` にはしない
（起動直後は既定値から始まるほうが分かりやすい／サーバ再起動で消えたジョブを復元しようとしない）。
ページをリロードすれば初期状態に戻る。

### 7.5 所要時間

`state/useJobTiming.ts` は**例外的なフック**（`Date.now()` の取得と決着検知のみ）で、
整形・比較・サーバ権威タイムスタンプの採否は `state/elapsed.ts` の純関数が受け持つ。
開始時刻を知らない経路（タブを離れて戻った再購読）では所要時間を**推測で出さない**。

---

## 8. 文書一覧

**版は各文書冒頭の `Version`、実装行数は `wc -l` の実測値（2026-09-24）。**

### 8.1 コンテナコンポーネント（状態・副作用・API を束ねる）

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `App.md` | `App.tsx` — タブ切替・パネルの振り分け・ヘッダーのモデル選択 | 174 | 1.7 | ★★ |
| `SupportPanel.md` | `components/SupportPanel.tsx` — 基本版 / GRACE-Support 共用 | 192 | 1.7 | ★★★ |
| `ReviewPanel.md` | `components/ReviewPanel.tsx` — GRACE-Review 本体 | 208 | 1.5 | ★★★ |
| `DataPanel.md` | `components/DataPanel.tsx` — データ管理タブの枠（サブタブ） | 111 | 1.5 | ★★ |
| `DataJobPanel.md` | `components/DataJobPanel.tsx` — チャンキング / Q/A 作成 / 登録ジョブ | 751 | 1.7 | ★★★ |
| `CollectionPanel.md` | `components/CollectionPanel.tsx` — コレクション管理 | 413 | 1.4 | ★★ |

### 8.2 入力・モーダル

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `QueryForm.md` | `components/QueryForm.tsx` | 272 | 1.7 | ★★★ |
| `ReviewForm.md` | `components/ReviewForm.tsx` | 254 | 1.7 | ★★ |
| `ConfirmModal.md` | `components/ConfirmModal.tsx` — HITL アクション承認 | 142 | 1.3 | ★★ |
| `QuestionSelectModal.md` | `components/QuestionSelectModal.tsx` — 0-(A) 主質問の選択 | 76 | 1.1 | ★★ |

### 8.3 表示コンポーネント

| 文書 | 対象 | 実装行数 | 版 | 重要度 |
|---|---|---:|---|:--:|
| `AnswerCard.md` | `components/AnswerCard.tsx` | 226 | 1.4 | ★★★ |
| `FindingList.md` | `components/FindingList.tsx` | 141 | 1.3 | ★★ |
| `Markdown.md` | `components/Markdown.tsx`（`markdown/parseMarkdown.ts`） | 114 | 1.2 | ★★ |
| `Timeline.md` | `components/Timeline.tsx` | 77 | 1.2 | ★★ |
| `StepTimeline.md` | `components/StepTimeline.tsx` | 45 | 1.2 | ★★ |
| `ReviewTimeline.md` | `components/ReviewTimeline.tsx` | 64 | 1.2 | ★ |
| `DocumentView.md` | `components/DocumentView.tsx` | 62 | 1.3 | ★ |
| `JobClock.md` | `components/JobClock.tsx` — 開始行 / 完了行 | 47 | 1.1 | ★ |
| `MetaErrorBanner.md` | `components/MetaErrorBanner.tsx` — メタ取得失敗の表示 | 24 | 1.1 | ★ |

### 8.4 横断文書

| 文書 | 内容 | 版 | 備考 |
|---|---|---|---|
| `README.md` | 本書（責務・構成・モジュール構造・棚卸し） | 2.5 | — |
| `review_ui.md` | GRACE-Review 画面全体の設計を俯瞰する**横断文書** | 1.7 | 対応する `.tsx` は無い。個別仕様は各 `<Component>.md` が正 |

---

## 9. 実装カバレッジ

`frontend/src/components/*.tsx` は **19 件**、`App.tsx` を加えて **20 件**。
対応する `<Component>.md` も **20 件**で、**欠落は無い**。

> 📌 `main.tsx`（10 行）・`types.ts`（431 行）・`api/client.ts`（301 行）・`styles.css`（1,342 行）には個別文書が無い。
> `types.ts` はバックエンドのスキーマと 1:1 で `backend/docs/reference/schemas.md` が正、
> `api/client.ts` は本書 §6 と各パネル文書の「API 通信」節が実質の記述である。**意図的に持たない。**

> ⚠️ コンポーネントを足した・消したら、同じコミットで `<Component>.md` と本書 §5・§8・§9 を更新すること。
> （実例: `ReviewPanel` / `ReviewForm` / `JobClock` / `MetaErrorBanner` の 4 件は 2026-09-12 まで文書が無かった。
> `ModelSelect.tsx` は 2026-09-23 に文書ごと削除した。）
>
> 📌 **「日付が古い ＝ 内容も古い」とは限らない**（2026-09-12 の突き合わせで、ヘッダー日付だけ遅れていた 6 件は
> 本文が実装と一致していた。逆に `SupportPanel.md` v1.2 は変更履歴だけ新しく本文が古かった）。
> **日付ではなく本文を実装と突き合わせて判断すること。**

---

## 10. state/ 純関数の一覧

`state/` は 21 モジュール（テストを除く）。役割で分類する。

| 分類 | モジュール | 行数 | 切り出した判断 |
|---|---|---:|---|
| **reducer** | `jobReducer.ts` | 173 | Support ジョブの状態遷移 |
| | `reviewReducer.ts` | 191 | Review ジョブの状態遷移 |
| | `dataReducer.ts` | 225 | データ準備ジョブの状態遷移（ジョブ種別でステップ ID が変わる） |
| **送信ペイロード** | `queryParams.ts` | 128 | 送信ペイロードの組み立て・基本版の vertical 固定・モデル未選択の null 化 |
| | `dataParams.ts` | 201 | データ準備フォーム → API パラメータ（空欄・トリム・null 化・未選択モデルのキー省略） |
| **モデル選択** | `headerModel.ts` | 126 | ヘッダーのモデルセレクタ（タブごとのスロット・`chunking_model` / `qa_model` を既定に使う・論理層の注記） |
| | `modelLabel.ts` | 42 | 見出し文字列・**単価つき**選択肢のラベル・Embedding の表示（`embeddingLabel`） |
| **ストア** | `formMemory.ts` | 120 | タブ切替時の入力退避と復元（モデルは含まない） |
| | `activeJobs.ts` | 45 | 実行中データジョブの `job_id` 保持（再マウント時の再購読） |
| **表示用の派生値** | `citations.ts` | 76 | 出典文字列（`[社内]` / `[Web]`）の解析 |
| | `highlight.ts` | 89 | 原文を非該当テキストと指摘スパンへ分割（XSS 回避のためデータだけ作る） |
| | `elapsed.ts` | 179 | 所要時間の整形・サーバ権威タイムスタンプの採否 |
| | `documentLimit.ts` | 52 | 文字数上限の判定・表示文言・アナウンス文言 |
| | `metaFetch.ts` | 53 | メタ取得失敗 → 対処可能な文言 |
| | `timelineAnnounce.ts` | 43 | 支援技術へ読み上げる 1 行 |
| | `interventionKind.ts` | 36 | 承認待ちが action（⑥）か question（0-(A)）か |
| **キー操作・a11y** | `submitKey.ts` | 49 | `QueryForm` / `ReviewForm` の送信キー（Ctrl+Enter / ⌘+Enter・IME 変換中は送信しない） |
| | `tabKeys.ts` | 49 | タブの矢印キー移動（roving tabindex） |
| | `selectionKeys.ts` | 63 | 指摘の選択キー（Enter / Space・IME 変換中は発火しない）と選択トグル |
| | `focusTrap.ts` | 62 | モーダル内の Tab 移動先（端で巻き戻す） |
| **フック（例外）** | `useJobTiming.ts` | 56 | **判断は持たず** `elapsed.ts` に委ねる。ここに分岐を足さない |

> `markdown/parseMarkdown.ts`（250 行）も同じ方針の純関数（`Markdown.md` が担当）。
>
> 📌 `focusTrap.ts` / `selectionKeys.ts` は 2026-09-24 に grace_v2_local から移植した。
> これで `frontend/src/` の**ファイル集合は両リポジトリで一致**したが、`modelLabel.ts` /
> `headerModel.ts` などは**中身が別物**なので、コピーで行き来させないこと（CLAUDE.md §5）。

---

## 11. テスト件数（実測）

**2026-09-26 に `cd frontend && npx vitest run` を実行した実測値。記憶で書かないこと。**

```
Test Files  23 passed (23)
     Tests  321 passed (321)
```

| テストファイル | 件数 |
|---|---:|
| `state/dataParams.test.ts` | 35 |
| `state/queryParams.test.ts` | 27 |
| `state/dataReducer.test.ts` | 24 |
| `state/elapsed.test.ts` | 22 |
| `components/ReviewForm.examples.test.ts` | 17 |
| `state/serverTiming.test.ts` | 16 |
| `state/headerModel.test.ts` | 16 |
| `markdown/parseMarkdown.test.ts` | 16 |
| `state/reviewReducer.test.ts` | 13 |
| `state/formMemory.test.ts` | 13 |
| `state/highlight.test.ts` | 13 |
| `state/citations.test.ts` | 13 |
| `state/tabKeys.test.ts` | 12 |
| `state/focusTrap.test.ts` | 12 |
| `state/documentLimit.test.ts` | 10 |
| `state/metaFetch.test.ts` | 10 |
| `state/submitKey.test.ts` | 10 |
| `state/timelineAnnounce.test.ts` | 9 |
| `state/selectionKeys.test.ts` | 9 |
| `state/activeJobs.test.ts` | 8 |
| `state/jobReducer.test.ts` | 7 |
| `state/interventionKind.test.ts` | 4 |
| `state/modelLabel.test.ts` | 5 |

> ⚠️ `serverTiming.test.ts` が検証するのは `elapsed.ts`（`state/serverTiming.ts` は**存在しない**）。
> ファイル名から実装を推測しないこと。
>
> 📌 テストの無い `state/` モジュールは `useJobTiming.ts`（フック・判断を持たない）のみ。

---

## 12. 検証手順

```bash
cd frontend
npm run lint     # tsc --noEmit
npm test         # vitest run
npm run build    # 本番ビルド
```

3 つとも CI の blocking ゲート（`frontend (tsc + vitest + build)`）に含まれる。
画面で確認するときは、リポジトリ直下で `./run_dev.sh`（backend :8000 + frontend :5173）を起動する。
`.env` の `ANTHROPIC_API_KEY`（LLM）/ `GOOGLE_API_KEY`（Embedding）と Qdrant の起動が前提（CLAUDE.md §2）。

---

## 13. 既知の問題・残タスク

| # | 内容 | 優先 |
|---|---|:--:|
| 1 | ~~ルート `README.md` のスクリーンショット残り 14 枚（`ANTHROPIC_API_KEY` と Qdrant のある環境が必要）~~ | ✅ **完了**（2026-09-26）。D-05〜D-08 を PR #210、残り 10 枚を PR #211 で撮影し、全 31 枚を掲載 |
| 2 | `ConfirmModal` の a11y ❌ 2 件（`Escape` で閉じない・閉じたあとのフォーカス復帰） | ⚠️ **判断のうえで未対応**（`ConfirmModal.md` §8）。実装漏れではない |

>
> 📌 `.running-banner` に `role` を足さないのは**意図的**である。実行中であることは
> `Timeline` の `aria-live` が読み上げており、バナーにも付けると二重読み上げになる。

詳細と根拠は [`docs/doc_modernization_todo.md`](../../docs/doc_modernization_todo.md) を参照。

<details>
<summary>完了済み（2026-09-12〜24）</summary>

| 内容 | 完了 |
|---|---|
| `ReviewPanel` / `ReviewForm` / `JobClock` / `MetaErrorBanner` の文書欠落 | 2026-09-12 |
| `SupportPanel.md` §4.1 が修正前のコード（`.catch(() => setVerticals([]))`）を載せていた | 2026-09-12（v1.3） |
| `frontend/docs` に索引が無く欠落を検知できなかった（本書） | 2026-09-12 |
| `review_ui.md` の位置づけ（横断文書として明記） | 2026-09-12（v1.3） |
| ヘッダー日付が古い 6 件の Props 突き合わせ（差分なし） | 2026-09-12 |
| `ReviewForm` のアクセシビリティ（`.sr-only` ラベル・`aria-invalid`・ライブ領域） | 2026-09-12 |
| `ReviewPanel` の打ち切り警告・`CollectionPanel` の中止バナーに `role`（banner 系すべてに付与） | 2026-09-12 |
| 未使用になった `ModelSelect.tsx` / `ModelSelect.md` と `modelLabel.ts` の未使用関数を削除 | 2026-09-23 |
| `ConfirmModal` のフォーカストラップ（`state/focusTrap.ts`）・指摘選択のキーボード操作（`state/selectionKeys.ts`）・`ReviewForm` の Ctrl+Enter 送信（grace_v2_local から移植） | 2026-09-24 |
| 全コンポーネント文書を `a_react_page_md_format.md` v1.1 へ追随（概要の「各責務対応のモジュール」・`## 1.` の「1.1 システム全体での位置づけ（3 層）」） | 2026-09-24 |

</details>

---

## 14. 変更履歴

| 版 | 日付 | 変更内容 |
|---|---|---|
| 2.5 | 2026-09-26 | Embedding のモデル名を画面に直書きするのをやめ、`GET /api/model` の `embedding_model` / `embedding_dims` から出すようにしたのに追随。§8 の版・実装行数（`App` 1.7 / 174・`DataPanel` 1.5 / 111・`DataJobPanel` 1.7 / 751・`modelLabel.ts` 42）、§11 のテスト件数を **23 ファイル / 321 件**（実測）へ更新 |
| 2.4 | 2026-09-26 | §13 残タスク 1（スクリーンショット残り 14 枚）を完了へ。PR #210（D-05〜D-08）と PR #211（残り 10 枚）で全 31 枚を撮影・掲載したのに、本表だけ未完のまま残っていた |
| 2.3 | 2026-09-24 | `AnswerCard.md` の Props を実装に追随させたのにあわせ §8 の版を更新（1.4）。§8 の本書自身の版（2.1 のままだった）も更新。§11 のテスト件数は `npx vitest run` で再実測し、記載どおり（23 ファイル / 318 件）であることを確認 |
| 2.2 | 2026-09-24 | コンポーネント文書 20 件を `a_react_page_md_format.md` v1.1 へ追随させた（2026-09-24）。§8 の版列を実測へ更新し、§13 の完了済みに追記 |
| 2.1 | 2026-09-24 | **a11y 3 点を grace_v2_local から移植したのに追随**（残タスク #2 を完了）。`state/focusTrap.ts` / `selectionKeys.ts` を §3・§5.4・§10 へ追加（21 モジュール）、§8 の版・行数を更新（`ConfirmModal` 1.2 / 142・`DocumentView` 1.2 / 62・`FindingList` 1.2 / 141・`ReviewForm` 1.6 / 254・`review_ui` 1.6）、テスト件数を **23 ファイル / 318 件**（実測）へ更新。§13 には `ConfirmModal` の判断済み未対応 2 件を残した |
| 2.0 | 2026-09-24 | **棚卸し索引から frontend の入口文書へ再構成**（grace_v2_local 側 README v2.0 と同じ構成）。§1 責務（やること / やらないこと）・§2 技術スタックとビルド構成・§3 ディレクトリ構成・§4 レイヤー構造と依存の向き（Mermaid）・§5 画面構成（タブ・ヘッダーのモデル選択と単価つきラベル・コンポーネントツリー・共用部品）・§6 バックエンドとの通信（SSE シーケンス図・エンドポイント一覧・取得失敗時の方針）・§7 状態管理の設計方針を新設。§8 の版・行数を実測で更新（`ReviewForm` 1.5・`review_ui` 1.5・`DataJobPanel` 1.5 / 739 行・`dataParams.ts` 201 行・`queryParams.ts` 128 行・`formMemory.ts` 120 行・`citations.ts` 76 行・`types.ts` 431 行・`api/client.ts` 301 行）。§10 を役割別に分類。§11 のテスト件数を再実測（**21 ファイル / 297 件**・変化なし）。§13 に grace_v2_local との a11y 差分（低優先）を追記し、完了済みを折りたたみへ移動。旧 §3.1（日付遅れ 6 件の検証記録）は §9 の注記へ要約 |
| 1.8 | 2026-09-23 | **`modelLabel.ts` の未使用関数を削除**（`formatModelLabel` / `defaultOptionLabel` / `DEFAULT_OPTION_FALLBACK`）。テスト件数を **21 ファイル / 297 件**（実測）へ更新 |
| 1.7 | 2026-09-23 | **未使用になった `ModelSelect.tsx` と `ModelSelect.md` を削除**し、文書一覧・実装カバレッジから外した（残タスク 8 を完了） |
| 1.6 | 2026-09-23 | **データ管理タブもヘッダーでモデルを選ぶ変更に追随。** `App.md` v1.5 / `DataPanel.md` v1.3 / `DataJobPanel.md` v1.4 / `ModelSelect.md` v1.3（**未使用**になった）の版と実装行数を更新。テスト件数を **21 ファイル / 304 件**（実測）へ更新 |
| 1.5 | 2026-09-23 | **モデル選択をヘッダー（`App`）へ移した変更に追随。** `App.md` v1.4 / `SupportPanel.md` v1.6 / `ReviewPanel.md` v1.4 / `QueryForm.md` v1.5 / `ReviewForm.md` v1.4 / `ModelSelect.md` v1.2 の版と実装行数を更新。`state/headerModel.ts` を §4 へ追加し、テスト件数を **21 ファイル / 301 件**（実測）へ更新 |
| 1.4 | 2026-09-16 | **モデルセレクタの追加に追随。** `ModelSelect.md` を新規作成し §2.2 へ追加。`QueryForm.md` v1.3 / `ReviewForm.md` v1.2 の版と実装行数を更新。`state/modelLabel.ts` を §4 へ追加し、テスト件数を **20 ファイル / 288 件**（実測）へ更新 |
| 1.3 | 2026-09-12 | 残タスク 7（`CollectionPanel` の中止バナー）を完了し、**banner 系 9 箇所すべてに `role` が付いた**。あわせて `SupportPanel.md` / `ReviewPanel.md` の「実行中であることが伝わるか ❌」を訂正（`Timeline` の `aria-live` が読み上げており、バナーに足すと二重読み上げになる） |
| 1.2 | 2026-09-12 | **アクセシビリティ改善に追随。** `ReviewForm` v1.1（`.sr-only` ラベル・`aria-invalid`・ライブ領域）と `ReviewPanel` v1.1（`role="alert"`）を反映。`state/documentLimit.ts`（純関数・10 件）を一覧へ追加し、テスト件数を 19 ファイル / 276 件へ更新。残タスクに `CollectionPanel` の同種 1 件を追加 |
| 1.1 | 2026-09-12 | 欠落 4 件（`ReviewPanel` / `ReviewForm` / `JobClock` / `MetaErrorBanner`）を新規作成して解消。ヘッダー日付が遅れていた 6 件を実装と突き合わせ、**差分が無いことを確認**。`review_ui.md` を横断文書として位置づけ直し。残タスクにアクセシビリティの 2 件を追加 |
| 1.0 | 2026-09-12 | 初版作成。文書一覧・実装カバレッジ（欠落 4 件）・state 純関数 16 件・テスト件数（`npm test` の実測 18 ファイル / 266 件）を記載 |
