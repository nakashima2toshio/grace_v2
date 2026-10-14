# api/data.py - データ準備ジョブ API ドキュメント

**Version 1.8** | 最終更新: 2026-10-14

> **本書の位置づけ**: `backend/app/api/data.py`（データ準備 4 ジョブの起動と共通 SSE / HITL）の **IPO リファレンス**。
> 引くための文書であり、**設計の「なぜ」と処理の流れは上位の文書が正本**である。
>
> | 知りたいこと | 参照先 |
> |---|---|
> | エンドポイント一覧と CONFIRM の要否 | [`README_backend_api.md` §4.0](README_backend_api.md) |
> | パイプラインの中身 | [`data_jobs.md`](../../core/docs/data_jobs.md) |
> | ジョブ基盤 | [`core_process_flow.md` §3](../../core/docs/core_process_flow.md) |
> | 文書全体の地図 | [`README_app.md`](../../docs/README_app.md) |

> **参考ドキュメント**
> - [`backend/app/core/docs/data_jobs.md`](../../core/docs/data_jobs.md) — 各ジョブの runner 実装
> - [`backend/app/core/docs/jobs.md`](../../core/docs/jobs.md) — ジョブ基盤（`JobManager` / SSE / HITL ブリッジ）
> - [`data_jobs.md`](../../core/docs/data_jobs.md) — データ準備パイプライン全体の設計

---

## 目次

- [概要](#概要)
- [1. アーキテクチャ構成図](#1-アーキテクチャ構成図)
- [2. エンドポイント一覧](#2-エンドポイント一覧)
- [3. エンドポイント IPO 詳細](#3-エンドポイント-ipo-詳細)
  - [使用例](#31-使用例)
- [4. 設定・定数](#4-設定定数)
- [5. 使用例](#5-使用例)
- [6. 変更履歴](#6-変更履歴)

---

## 概要

`backend/app/api/data.py` は、データ準備パイプライン（チャンク化 / Q/A 生成 / Qdrant 登録 / コレクション削除）を
**非同期ジョブとして起動し、SSE で進捗を配信する** API 層である。

`api/support.py` / `api/review.py` と**構造は同一**。違うのはジョブのパラメータ型と結果の形だけで、
ジョブ基盤・SSE・HITL ブリッジは `core/jobs.py` をそのまま使う。

### 主な責務

- 4 種のジョブ（チャンク化 / Q/A 生成 / 登録 / 削除）を `job_manager.start()` で起動し `202 Accepted` を返す
- 進捗を SSE（`text/event-stream`）で逐次配信する
- HITL CONFIRM への応答（承認 / 拒否）を注入する
- ジョブの状態と結果をポーリングで返す（SSE のフォールバック）

### 各責務対応のモジュール

| # | 責務 | 対応モジュール | 説明 |
|---|------|--------------|------|
| 1 | ジョブ起動 | `core/jobs.py` | `job_manager.start(params)` が params の型から runner を解決 |
| 2 | 実処理 | `core/data_jobs.py` | `_chunking_runner` / `_qa_runner` / `_register_runner` / `_delete_runner` |
| 3 | 進捗の横取り | `core/job_logs.py` | 既存パッケージの `logging` 出力を log イベントへ転送 |
| 4 | リクエスト／レスポンス型 | `backend/app/schemas.py` | `ChunkingRequest` / `QaGenerationRequest` / `RegisterRequest` / `DeleteCollectionsRequest` ほか |

### 主要機能一覧

| 機能 | 説明 |
|------|------|
| `run_chunking(request)` | チャンク化ジョブを起動（承認なし） |
| `generate_qa(request)` | チャンク済み CSV から Q/A を生成（承認なし） |
| `register_collection(request)` | Q/A CSV を Qdrant へ登録（`recreate=True` のときだけ承認） |
| `delete_collections(request)` | コレクション削除（**常に**承認） |
| `stream_events(job_id)` | 進捗を SSE で配信（4 種で共通） |
| `confirm_intervention(job_id, request)` | HITL CONFIRM への応答を注入（4 種で共通） |
| `get_result(job_id)` | ジョブの状態・結果を返す（ポーリング用） |

---

## 1. アーキテクチャ構成図

```mermaid
flowchart TB
    subgraph CLIENT["フロントエンド"]
        UI["データ管理タブ"]
        MODAL["ConfirmModal"]
    end

    subgraph API["backend/app/api/data.py"]
        POST3["POST /api/chunking/run<br/>/qa/generate<br/>/qdrant/register<br/>/qdrant/delete"]
        SSE["GET /api/data/stream/{job_id}"]
        CONFIRM["POST /api/data/confirm/{job_id}"]
        RESULT["GET /api/data/result/{job_id}"]
    end

    subgraph CORE["ジョブ基盤"]
        JM["core/jobs.py :: job_manager"]
        RUNNER["core/data_jobs.py :: 3 runner"]
        CAPTURE["core/job_logs.py :: capture_logs()"]
    end

    subgraph EXT["実処理（既存パッケージ・無改修）"]
        CHUNK["chunking/"]
        QAQ["qa_qdrant/"]
        SVC["services/data_pipeline_service.py"]
    end

    UI --> POST3
    POST3 --> JM
    JM --> RUNNER
    RUNNER --> CAPTURE
    RUNNER --> CHUNK
    RUNNER --> QAQ
    RUNNER --> SVC
    RUNNER --> SSE
    SSE --> UI
    RUNNER --> MODAL
    MODAL --> CONFIRM
    CONFIRM --> JM
    UI --> RESULT
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class UI,MODAL,POST3,SSE,CONFIRM,RESULT,JM,RUNNER,CAPTURE,CHUNK,QAQ,SVC default
style CLIENT fill:#1a1a1a,stroke:#fff,color:#fff
style API fill:#1a1a1a,stroke:#fff,color:#fff
style CORE fill:#1a1a1a,stroke:#fff,color:#fff
style EXT fill:#1a1a1a,stroke:#fff,color:#fff
```

---

## 2. エンドポイント一覧

| メソッド | パス | ステータス | レスポンス | CONFIRM |
|---|---|---|---|---|
| POST | `/api/chunking/run` | 202 | `QueryAccepted` | なし（非破壊） |
| POST | `/api/qa/generate` | 202 | `QueryAccepted` | なし（非破壊） |
| POST | `/api/qdrant/register` | 202 | `QueryAccepted` | `recreate=True` のときだけ |
| POST | `/api/qdrant/delete` | 202 | `QueryAccepted` | **常に** |
| GET | `/api/data/stream/{job_id}` | 200 | `text/event-stream` | — |
| POST | `/api/data/confirm/{job_id}` | 200 | `ConfirmResponse` | — |
| GET | `/api/data/result/{job_id}` | 200 | `DataJobStatusResponse` | — |

> 📝 **SSE と HITL 応答は 4 種で共通のエンドポイントにまとめてある。**
> ジョブ種別ごとに分けても中身が同じになるため。種別は `job.kind` が持つ。

> ⚠️ **`backend.app.core.data_jobs` の import には副作用がある。**
> import 時に `register_runner()` が 4 件走る。パラメータ型を使う以上この import は
> 必ず発生するので、**登録漏れは構造的に起きない**（`review_agent.py` と同じ方式）。

---

## 3. エンドポイント IPO 詳細

### 3.1 使用例

| # | パターン | いつ使うか | 例 |
|---|---------|-----------|----|
| 1 | **基本**: 入力ファイルの確認 → ジョブ起動 → SSE → 結果 | 非破壊のジョブ（チャンク化・Q/A 生成）を動かす | 3.1.1 |
| 2 | 破壊的な操作は CONFIRM を通る（拒否 → 承認） | 削除・`recreate=True` の登録 | 3.1.2 |

> 📝 **確かめ方（2026-10-11）**: どちらも `PYTHONPATH=. python3 <例>.py` で実行した。3.1.1 は LLM を呼ぶ手前で失敗する入力にしてある（API キーの有無で 2 通り）。
> 3.1.2 は VM の実物の Qdrant（`docker compose` で起動）に 4 次元の一時コレクションを作り、本物の削除ジョブで消した。

#### 3.1.1 基本: 入力ファイルの確認 → ジョブ起動 → SSE → 結果

```python
import json
from fastapi.testclient import TestClient
from backend.app.main import app

c = TestClient(app)

# 1. 入力候補を見る（許可ディレクトリの中だけ。?dir= で切り替える）
files = c.get("/api/files", params={"dir": "OUTPUT"}).json()
print(files["allowed_dirs"], [f["path"] for f in files["files"]][:2])

# 2. ジョブを起動する（入力の検証は runner 側。ここでは常に 202 + job_id）
r = c.post("/api/chunking/run", json={"input_file": "../etc/passwd"})
print(r.status_code, r.json()["stream_url"].rsplit("/", 1)[0])
job_id = r.json()["job_id"]

# 3. SSE を読む（承認待ちの無いジョブなら TestClient でも最後まで読める）
with c.stream("GET", f"/api/data/stream/{job_id}") as s:
    for line in s.iter_lines():
        if line.startswith("data: "):
            ev = json.loads(line[6:])
            print(ev["type"], ev.get("status"), ev.get("message", "")[:60])

# 4. 結果を取る
res = c.get(f"/api/data/result/{job_id}").json()
print(res["status"], res["kind"], res["result"])

# 実行結果（ANTHROPIC_API_KEY が無い環境）:
# ['OUTPUT', 'output_chunked', 'qa_output', 'datasets'] ['OUTPUT/cc_news_2per_768.csv', 'OUTPUT/cc_news_2per.csv']
# 202 /api/data/stream
# error None ⚠️ ANTHROPIC_API_KEY が未設定です。.env に設定してください。
# done failed
# failed chunking None
#
# 実行結果（キーがある環境。入力パスの検証で止まる）:
# 202 /api/data/stream
# step started
# error None ❌ 入力ファイルを開けません: 入力パスは 'ディレクトリ名/ファイル名' の形式で指定してください: '../etc/
# done failed
# failed chunking None
```

> ⚠️ **入力ファイルの誤りは 400 ではなく、ジョブの失敗（`error` イベント → `status: failed`）で返る。** 検証は runner（`core/data_jobs.py`）が行い、
> 4 種の API を同じ形（常に 202）にそろえている。許可ディレクトリの外・`../` を含む指定は `services/data_pipeline_service.py` のホワイトリストで弾く。
> 実際にチャンク化まで進めると LLM を呼ぶ（課金される）。画面から流す手順は [`data_jobs.md` §6](../../core/docs/data_jobs.md)。

#### 3.1.2 破壊的操作は CONFIRM を通る

削除は常に、登録は `recreate=True` のときだけ承認待ちになる。承認しなければ（拒否・タイムアウト）実行しない。

> ⚠️ **承認待ちになるジョブの SSE は本物のサーバで読む。** `TestClient` は応答を最後まで溜めてから返すので、承認を送れないまま
> タイムアウト（安全側＝実行しない）まで待つことになる（[`support.md` §4.1.1](support.md#41-使用例)）。

```python
import json, threading, time

import httpx
import uvicorn
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from backend.app.main import app

# 例のための一時コレクション（4 次元・空）
q = QdrantClient(url="http://localhost:6333")
q.create_collection("datadoc_demo", vectors_config=VectorParams(size=4, distance=Distance.COSINE))

# SSE を逐次読むため本物のサーバで起動する（TestClient は応答を溜めてから返す）
server = uvicorn.Server(uvicorn.Config(app, port=8768, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
while not server.started:
    time.sleep(0.05)


def delete(c, approve):
    """削除ジョブを起動し、承認待ちが来たら approve を返して、結果を返す。"""
    job_id = c.post("/api/qdrant/delete", json={"collections": ["datadoc_demo"]}).json()["job_id"]
    with c.stream("GET", f"/api/data/stream/{job_id}") as s:
        for line in s.iter_lines():
            if not line.startswith("data: "):
                continue
            ev = json.loads(line[6:])
            if ev["type"] == "intervention" and ev["status"] == "waiting":
                print("  承認待ち:", ev["message"].splitlines()[0])
                c.post(f"/api/data/confirm/{job_id}",
                       json={"intervention_id": ev["data"]["intervention_id"], "approve": approve})
    return c.get(f"/api/data/result/{job_id}").json()


with httpx.Client(base_url="http://127.0.0.1:8768", trust_env=False) as c:
    for approve in (False, True):
        res = delete(c, approve)
        print(f"approve={approve}:", res["status"], res["result"],
              "残っている" if q.collection_exists("datadoc_demo") else "消えた")
server.should_exit = True

# 実行結果:
#   承認待ち: コレクション 1 件（datadoc_demo）を削除します。合計 0 件のデータが失われ、元に戻せません。実行してよろしいですか？
# approve=False: completed {'kind': 'delete', 'deleted': [], 'failed': [], 'missing': [], 'cancelled': True, 'reason': '承認されませんでした'} 残っている
#   承認待ち: コレクション 1 件（datadoc_demo）を削除します。合計 0 件のデータが失われ、元に戻せません。実行してよろしいですか？
# approve=True: completed {'kind': 'delete', 'deleted': ['datadoc_demo'], 'failed': [], 'missing': [], 'cancelled': False, 'total_points': 0} 消えた
```

> 📌 拒否しても `status` は `completed`（ジョブ自体は正常に終わり、`result.cancelled` が `True`）。承認待ちのメッセージには失われる件数が入る。

### 3.2 `run_chunking`

```python
@router.post("/chunking/run", response_model=QueryAccepted, status_code=202)
def run_chunking(request: ChunkingRequest) -> QueryAccepted
```

| 項目 | 内容 |
|------|------|
| **Input** | `ChunkingRequest`（`input_file` / `output_dir` / `model` / `workers` / `block_size` / `text_column` / `max_rows` / `combine_rows` / `resume` / `verbose`） |
| **Process** | `ChunkingParams` へ詰め替えて `job_manager.start()` |
| **Output** | `QueryAccepted(job_id, stream_url)` — `202 Accepted` |

> 📝 **入力ファイルの検証はここでしない。** 許可ディレクトリ外・不在なら runner 側が
> error イベントを流してジョブが失敗する。400 を返さないのは、**起動と検証の責務を
> runner に寄せて 4 種の API を同じ形にするため**。

### 3.3 `generate_qa`

```python
@router.post("/qa/generate", response_model=QueryAccepted, status_code=202)
def generate_qa(request: QaGenerationRequest) -> QueryAccepted
```

| 項目 | 内容 |
|------|------|
| **Input** | `QaGenerationRequest`（`input_file` / `output_dir` / `model` / `max_docs` / `use_celery` / `concurrency` / `analyze_coverage` / `verbose`） |
| **Process** | `QaGenerationParams` へ詰め替えて `job_manager.start()` |
| **Output** | `QueryAccepted(job_id, stream_url)` — `202 Accepted` |

> 📝 入力は**チャンク済み CSV**（`/api/chunking/run` の出力）。出力の Q/A CSV は
> そのまま `/api/qdrant/register` の入力になる。パイプラインの流れは
> **チャンク化 → Q/A 生成 → Qdrant 登録**。

> ⚠️ **`use_celery=True` を渡すなら Celery ワーカーが起動していること。**
> 落ちている場合はジョブが error イベントで失敗する。起動時に弾かないのは、
> ワーカーの生死が起動から実行までの間に変わりうるため（実行時に確かめる）。

### 3.4 `register_collection`

```python
@router.post("/qdrant/register", response_model=QueryAccepted, status_code=202)
def register_collection(request: RegisterRequest) -> QueryAccepted
```

| 項目 | 内容 |
|------|------|
| **Input** | `RegisterRequest`（`input_file` / `collection` / `recreate` / `batch_size` / `embed_workers` / `text_col` / `domain` / `max_docs` / `provider` / `normalize_filename` / `create_ui_csv` / `ui_output_dir` / `verbose`） |
| **Process** | `RegisterParams` へ詰め替えて `job_manager.start()` |
| **Output** | `QueryAccepted(job_id, stream_url)` |

> ⚠️ **`recreate=True` のときだけ intervention イベントが流れる。**
> 既存コレクションを削除して作り直すため。フロントは既存の `ConfirmModal` で承認を返す。

> 📝 **入力は「既に作られた Q/A CSV」である。** Q/A 生成そのものは UI に無く CLI のみ。

### 3.5 `delete_collections`

```python
@router.post("/qdrant/delete", response_model=QueryAccepted, status_code=202)
def delete_collections(request: DeleteCollectionsRequest) -> QueryAccepted
```

| 項目 | 内容 |
|------|------|
| **Input** | `DeleteCollectionsRequest`（`collections: List[str]` / `verbose`） |
| **Process** | `DeleteParams` へ詰め替えて `job_manager.start()` |
| **Output** | `QueryAccepted(job_id, stream_url)` |

> ⚠️ **HTTP の `DELETE` メソッドにしていない。**
> 承認を経ずに消える経路を作らないため。削除は不可逆なので、
> **必ず intervention → 承認 → 実行**を通す。

### 3.6 `stream_events`

```python
@router.get("/data/stream/{job_id}")
def stream_events(job_id: str) -> StreamingResponse
```

| 項目 | 内容 |
|------|------|
| **Input** | `job_id` |
| **Process** | `job_manager.get(job_id)`（無ければ **404**）。`job.stream_events()` を回し、`None` は `SSE_KEEPALIVE`（`"event: keepalive\ndata: {}\n\n"` の名前付きイベント）、それ以外は `data: {json}\n\n` として yield。最後に `done_event(job)`（`type` / `status` / `ts` / `started_at`）を送る |
| **Output** | `StreamingResponse`（`media_type="text/event-stream"`、`Cache-Control: no-cache` / `X-Accel-Buffering: no`） |

> 📝 **形式は Support / Review と完全に同一。** 既存パッケージの `logging` 出力は
> `core/job_logs.py` が横取りして log イベントとして流れてくる。
> **イベントは常に先頭からリプレイされる**ため、再接続しても取りこぼさない。

> 📝 `X-Accel-Buffering: no` は nginx 等のリバースプロキシがバッファリングして
> SSE が届かなくなるのを防ぐため。

### 3.7 `confirm_intervention`

```python
@router.post("/data/confirm/{job_id}", response_model=ConfirmResponse)
def confirm_intervention(job_id: str, request: ConfirmRequest) -> ConfirmResponse
```

| 項目 | 内容 |
|------|------|
| **Input** | `job_id`、`ConfirmRequest(intervention_id, approve)` |
| **Process** | `job_manager.confirm(job_id, intervention_id, approve)`。戻り値が `"not_found"` なら **404** |
| **Output** | `ConfirmResponse(status)` |

> ⚠️ **拒否・タイムアウトの場合、削除も再作成も実行されない**（安全側）。

### 3.8 `get_result`

```python
@router.get("/data/result/{job_id}", response_model=DataJobStatusResponse)
def get_result(job_id: str) -> DataJobStatusResponse
```

| 項目 | 内容 |
|------|------|
| **Input** | `job_id` |
| **Process** | `job_manager.get(job_id)`（無ければ **404**） |
| **Output** | `DataJobStatusResponse(job_id, kind, status, result)` |

> 📝 **`result` は素の dict のまま返す。** 結果の形はジョブ種別で違うため、
> `kind`（`"chunking"` / `"register"` / `"delete"`）で判別させる。

---

## 4. 設定・定数

| 名前 | 値 | 説明 |
|---|---|---|
| `router` | `APIRouter(prefix="/api", tags=["data"])` | 全エンドポイントの接頭辞 |
| `_STREAM_URL` | `"/api/data/stream/{job_id}"` | 3 種で共通の SSE URL |

---

## 5. 使用例

```bash
# ① チャンク化を起動
curl -X POST http://localhost:8000/api/chunking/run \
  -H 'Content-Type: application/json' \
  -d '{"input_file": "OUTPUT/cc_news_1per.csv", "output_dir": "output_chunked"}'
# → {"job_id": "...", "stream_url": "/api/data/stream/..."}

# ② 進捗を SSE で受ける
curl -N http://localhost:8000/api/data/stream/<job_id>

# ③ CONFIRM が来たら承認を返す（削除・recreate 時）
curl -X POST http://localhost:8000/api/data/confirm/<job_id> \
  -H 'Content-Type: application/json' \
  -d '{"intervention_id": "...", "approve": true}'

# ④ 結果を取る（SSE を使わない場合）
curl http://localhost:8000/api/data/result/<job_id>
```

---

## 6. 変更履歴

| バージョン | 日付 | 変更内容 |
|---|---|---|
| 1.0 | — | 初版作成。`backend/app/api/data.py`（160 行）の 6 エンドポイントを IPO 形式で記述。3 種のジョブと CONFIRM の要否、SSE / HITL を共通エンドポイントにまとめた理由、`DELETE` メソッドを使わない理由、入力検証を runner に寄せた理由を実コードのコメントから起こして記載 |
| 1.1 | — | **`POST /api/qa/generate` を追加**（`QaGenerationRequest` → `QaGenerationParams`）。ジョブは 4 種になり、SSE / HITL の共通エンドポイントもそのまま 4 種で共有する。§3 の節番号を繰り下げ |
| 1.2 | 2026-09-15 | **§3.1「使用例」を新設**（2026-09-15）。ドキュメント規約 `a_class_method_md_format.md` §6.1 が IPO 詳細セクションの冒頭に必須としている代表ワークフローが欠落していた。入力候補の確認 → チャンク化ジョブ起動、破壊的操作の CONFIRM 経路の 2 本を追加し、**実行して出力を確認した**（外部依存が要る例はその旨を明記）。旧 §3.1〜§3.7 は §3.2〜§3.8 へ繰り下げ |
| 1.3 | 2026-09-16 | 3 階建て再編（`reference/` へ移設）に伴い、冒頭へ**位置づけと上位文書への導線**を追加した |
| 1.4 | 2026-10-08 | SSE の keepalive を名前付きイベントへ変更したのに追随（姉妹リポジトリ grace_v2_local で、長い処理中に画面への配信が黙って止まった件の移植。フロントは 60 秒無音で張り直す） |
| 1.5 | 2026-10-09 | `POST /api/qa/generate` の入力から `batch_chunks` を削除したのに追随（2026-10-09） |
| 1.6 | 2026-10-11 | `backend/docs/reference/api_data.md` から移した（`a_cross_doc_md_format.md` §1.1.2。リンクを付け替えた）。§3.1 を作り直した。3.1.1 は入力の誤りが 400 ではなくジョブの失敗で返ることを実行で確かめ、3.1.2 は実物の Qdrant に一時コレクションを作って削除ジョブの拒否 → 承認を通した（以前の例は承認の往復を実行していなかった） |
| 1.7 | 2026-10-12 | backend/docs/ の横断文書の廃止（2026-10-12）に追随し、参照先を backend/app/docs/README_app.md・backend/app/api/docs/README_api.md・backend/app/core/docs/core_process_flow.md などへ付け替えた |
| 1.8 | 2026-10-14 | 索引の改名（frontend/docs/README.md → README_frontend.md、README_api.md → README_backend_api.md、README_core.md → README_backend_core.md）に合わせて参照を付け替えた |
