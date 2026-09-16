# API 契約（エンドポイント・SSE・ステータス） ドキュメント

**Version 1.0** | 最終更新: 2026-09-16

> **本書の位置づけ**: backend が外へ約束している**契約**をまとめる。
> エンドポイント一覧・SSE のワイヤ形式・HTTP ステータスの使い分け・
> `frontend/src/types.ts` との対応。フィールド単位の定義は
> [`schemas.md`](./reference/schemas.md)（`backend/app/schemas.py` の逐条解説）を参照する。

> ⚠️ **これは内部仕様ではなく契約である。** CI の frontend ゲートは
> `frontend/src/types.ts` の型エラー 1 個でマージを止める。
> **API スキーマを変えたら `types.ts` を同じ PR で追随させること。**

> **関連ドキュメント**
> - [`architecture.md`](./architecture.md) / [`job_runtime.md`](./job_runtime.md)
> - [`schemas.md`](./reference/schemas.md) — Pydantic モデルのフィールド定義
> - [`reference/api_support.md`](./reference/api_support.md) ほか `reference/api_*.md`

---

## 目次

- [1. エンドポイント一覧](#1-エンドポイント一覧)
- [2. 非同期ジョブの 3 点セット](#2-非同期ジョブの-3-点セット)
- [3. SSE のワイヤ形式](#3-sse-のワイヤ形式)
- [4. HITL CONFIRM の往復](#4-hitl-confirm-の往復)
- [5. HTTP ステータスの使い分け](#5-http-ステータスの使い分け)
- [6. スキーマ ↔ types.ts 対応表](#6-スキーマ--typests-対応表)
- [7. 変更履歴](#7-変更履歴)

---

## 1. エンドポイント一覧

全 23 エンドポイント。ベース URL は `http://localhost:8000`。**認証は無い。**

### 1.1 GRACE-Support（`api/support.py`）

| Method | パス | 状態 | 説明 |
|---|---|---:|---|
| POST | `/api/support/query` | 202 | 問い合わせジョブ起動 → `{job_id, stream_url}` |
| GET | `/api/support/stream/{job_id}` | 200 | SSE でステップ進捗（0-(A)〜⑥） |
| POST | `/api/support/confirm/{job_id}` | 200 | HITL 応答（承認 / 拒否 / 選択肢） |
| GET | `/api/support/result/{job_id}` | 200 | 状態と `SupportResult`（ポーリング用） |

### 1.2 GRACE-Review（`api/review.py`）

| Method | パス | 状態 | 説明 |
|---|---|---:|---|
| POST | `/api/review/submit` | 202 | レビュージョブ起動（文書は最大 `MAX_DOCUMENT_CHARS` = 50,000 字） |
| GET | `/api/review/stream/{job_id}` | 200 | SSE でステップ進捗（S1・①〜⑦） |
| POST | `/api/review/confirm/{job_id}` | 200 | HITL 応答 |
| GET | `/api/review/result/{job_id}` | 200 | 状態と `ReviewResult` |

### 1.3 データ準備ジョブ（`api/data.py`）

起動は 4 本に分かれるが、**SSE / CONFIRM / 結果取得は 1 組を共用**する。

| Method | パス | 状態 | CONFIRM | 説明 |
|---|---|---:|---|---|
| POST | `/api/chunking/run` | 202 | なし | チャンク化（非破壊） |
| POST | `/api/qa/generate` | 202 | なし | Q/A 生成（非破壊・出力は新規ファイル） |
| POST | `/api/qdrant/register` | 202 | `recreate=true` のときだけ | Q/A CSV を Qdrant へ登録 |
| POST | `/api/qdrant/delete` | 202 | **常に** | コレクション削除 |
| GET | `/api/data/stream/{job_id}` | 200 | — | 4 種共通の SSE |
| POST | `/api/data/confirm/{job_id}` | 200 | — | 4 種共通の HITL 応答 |
| GET | `/api/data/result/{job_id}` | 200 | — | 4 種共通の結果取得 |

### 1.4 Qdrant 参照系（`api/qdrant.py`）— 読み取り専用

| Method | パス | 状態 | 説明 |
|---|---|---:|---|
| GET | `/api/qdrant/health` | **200 固定** | 稼働確認（落ちていても 200・本文の `available` で判定） |
| GET | `/api/qdrant/collections` | 200 / 503 | コレクション一覧 |
| GET | `/api/qdrant/collections/{name}` | 200 / 404 / 503 | コレクション詳細 |
| GET | `/api/qdrant/collections/{name}/points` | 200 / 404 / 503 | ポイントのプレビュー（`limit` 1〜500・既定 50） |
| GET | `/api/files` | 200 / 400 | 入力ファイル候補（`dir` は許可ディレクトリのみ・絶対パスは返さない） |

### 1.5 メタ情報（`api/meta.py`）

| Method | パス | 状態 | 説明 |
|---|---|---:|---|
| GET | `/api/verticals` | 200 | 業界プロファイル一覧（gov / saas / ec） |
| GET | `/api/rulesets` | 200 | ルールセット一覧（**ルール本文は返さない**・件数と法令のみ） |
| GET | `/api/health` | 200 | 稼働確認と API キー設定の有無（**値は返さない**） |

---

## 2. 非同期ジョブの 3 点セット

Support / Review / データ準備は**同じ 3 点セット**で動く。

```
POST   …/query|submit|run     → 202 {job_id, stream_url}
GET    {stream_url}           → SSE（進捗・介入・結果・done 番兵）
POST   …/confirm/{job_id}     → HITL 応答（必要なときだけ）
GET    …/result/{job_id}      → ポーリング用フォールバック
```

`stream_url` は**サーバが返す**（クライアントで組み立てない）。系統ごとに
`/api/support/stream/...` `/api/review/stream/...` `/api/data/stream/...` と違うため。

---

## 3. SSE のワイヤ形式

3 系統で**完全に同一**。フロントは同じパーサを使える。

```
data: {"seq":0,"ts":1758000000.0,"type":"step","step":"plan","status":"started", ...}

: keepalive

data: {"type":"done","status":"completed","ts":...,"started_at":...}
```

| 約束 | 内容 |
|---|---|
| イベント名 | **付けない**（`event:` 行を出さない）。種別は JSON の `type` で判定する |
| メッセージ | `data: ` + `SupportEventModel` の JSON 1 行（`ensure_ascii=False`） |
| keepalive | `: keepalive` のコメント行（15 秒新イベントが無いとき） |
| 終端 | `type:"done"` の番兵 1 通。フロントはこれで `EventSource` を閉じる |
| リプレイ | **常に seq=0 から**配信する。途中購読・再接続でも取りこぼさない |
| ヘッダ | `Cache-Control: no-cache` / `X-Accel-Buffering: no` |

`type` の値は `step` / `log` / `intervention` / `result` / `error` の 5 種
（＋終端の `done`）。詳細は [`job_runtime.md` §2](./job_runtime.md)。

### ステップ ID

| 系統 | 定数 | 値 |
|---|---|---|
| Support | `STEP_IDS` | `analyze` `profile` `plan` `execute` `confidence` `gate` `web` `no_info` `action` |
| Review | `REVIEW_STEP_IDS` | `ruleset` `segment` `retrieve` `detect` `ground` `suppress` `web` `severity` `action` |
| チャンク化 | `CHUNKING_STEP_IDS` | `load` `chunk` `save` |
| Q/A 生成 | `QA_STEP_IDS` | `load` `generate` `coverage` `save` |
| 登録 | `REGISTER_STEP_IDS` | `prepare` `confirm` `embed` `upsert` |
| 削除 | `DELETE_STEP_IDS` | `inspect` `confirm` `delete` |

> ⚠️ **ステップ ID の並びは実行順であって、CLAUDE.md の番号（①〜⑦）とは一致しない。**
> Support の `no_info`（④'）は `web`（⑤）の後、Review の `severity`（⑤）は
> `web`（⑥）の後に来る。

---

## 4. HITL CONFIRM の往復

```
SSE  → {"type":"intervention","status":"waiting","data":{"intervention_id":"...","timeout_seconds":300, ...}}
POST → /api/{support|review|data}/confirm/{job_id}
       {"intervention_id":"...","approve":true,"selected_option":null}
SSE  → {"type":"intervention","status":"resolved","data":{"action":"proceed"}}
```

`ConfirmResponse.status` の値は 3 つ。

| 値 | 意味 | HTTP |
|---|---|---|
| `resolved` | 応答を注入できた | 200 |
| `not_waiting` | その `intervention_id` は待機中でない（タイムアウト済み・ID 違い） | **200**（エラーにしない） |
| `not_found` | ジョブが存在しない | 404 |

**無応答のまま `timeout_seconds` を過ぎると `status:"timeout"` が流れ、
アクションは実行されない**（安全側）。`selected_option` は選択肢つき介入
（0-(A) 主質問の選択）でのみ使い、通常の承認では省略する。

---

## 5. HTTP ステータスの使い分け

| ステータス | 使う場面 |
|---|---|
| **200** | 参照系・SSE・CONFIRM 応答（`not_waiting` を含む） |
| **202** | ジョブ起動（実処理はワーカースレッドへ委ねる） |
| **400** | 許可ディレクトリ外の指定（`/api/files`） |
| **404** | ジョブ ID が無い / コレクションが無い |
| **422** | Pydantic のバリデーション違反（文書長超過など。FastAPI が自動で返す） |
| **503** | Qdrant へ接続できない（**参照系のみ**） |

### ⚠️ `/api/qdrant/health` だけは 200 固定

Qdrant が落ちていても 200 を返し、本文の `available: false` と理由で伝える。
503 にすると、画面側で「通信エラー」と「Qdrant を起動してください」を
**出し分けられなくなる**ためである。一覧・詳細は Qdrant が必須なので 503 を返す。

---

## 6. スキーマ ↔ types.ts 対応表

`backend/app/schemas.py` の Pydantic モデルと `frontend/src/types.ts` の対応。
**片方だけ変えると frontend ゲートで落ちる。**

| backend（`schemas.py`） | frontend（`types.ts`） | 使う画面 |
|---|---|---|
| `QueryRequest` | `QueryParams` | SupportPanel |
| `SupportResultModel` | `SupportResult` | SupportPanel |
| `SupportEventModel` | `SupportEvent` | 全パネル（SSE 共通） |
| `VerticalInfo` | `VerticalInfo` | SupportPanel（プロファイル選択） |
| `ReviewRequest` | `ReviewParams` | ReviewPanel |
| `ReviewResultModel` / `ReviewFindingModel` / `SegmentModel` / `FindingSummaryModel` | `ReviewResult` / `ReviewFinding` / `Segment` / `FindingSummary` | ReviewPanel |
| `RuleSetInfo` | `RuleSetInfo` | ReviewPanel（ルールセット選択） |
| `QdrantHealth` / `CollectionInfo` / `CollectionDetail` / `CollectionPoints` | 同名 | DataPanel（コレクション管理） |
| `InputFileInfo` / `InputFileListResponse` | 同名 | DataPanel（入力選択） |
| `ChunkingRequest` / `QaGenerationRequest` / `RegisterRequest` | `ChunkingParams` / `QaParams` / `RegisterParams` | DataPanel |
| `DataJobStatusResponse` | `DataJobStatusResponse` / `DataJobResult` / `DataJobKind` | DataPanel |
| `ConfirmRequest` / `ConfirmResponse` | `InterventionInfo` 経由 | ConfirmModal / QuestionSelectModal |

---

## 7. 変更履歴

| Version | 日付 | 変更内容 |
|---|---|---|
| 1.0 | 2026-09-16 | 新規作成。全 23 エンドポイント・SSE ワイヤ形式・ステータス方針・types.ts 対応を実装から書き起こした |
