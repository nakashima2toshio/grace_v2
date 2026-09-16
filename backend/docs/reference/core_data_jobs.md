# core/data_jobs.py - データ準備ジョブ runner ドキュメント

**Version 1.4** | 最終更新: 2026-09-16

> **本書の位置づけ**: `backend/app/core/data_jobs.py`（データ準備 4 ジョブの runner）の **IPO リファレンス**。
> 引くための文書であり、**設計の「なぜ」と処理の流れは上位の文書が正本**である。
>
> | 知りたいこと | 参照先 |
> |---|---|
> | パイプラインの中身 | [`data_pipeline.md`](../data_pipeline.md) |
> | ジョブ基盤・runner 注入 | [`job_runtime.md` §3](../job_runtime.md) |
> | LLM と Embedding のプロバイダ分離 | [`config_and_providers.md`](../config_and_providers.md) |
> | 文書全体の地図 | [`README.md`](../README.md) |

> **参考ドキュメント**
> - [`backend/docs/reference/api_data.md`](./api_data.md) — 本モジュールを起動する API 層
> - [`backend/docs/reference/core_jobs.md`](./core_jobs.md) — ジョブ基盤（`register_runner` / `JobManager`）
> - [`backend/docs/reference/core_job_logs.md`](./core_job_logs.md) — `capture_logs()` の仕組み
> - [`backend/docs/data_pipeline.md`](../data_pipeline.md) — パイプライン全体の設計

---

## 目次

- [概要](#概要)
- [1. アーキテクチャ構成図](#1-アーキテクチャ構成図)
- [2. ステップ定義](#2-ステップ定義)
- [3. クラス・関数一覧表](#3-クラス関数一覧表)
- [4. パラメータ IPO 詳細](#4-パラメータ-ipo-詳細)
  - [使用例](#41-使用例)
- [5. runner IPO 詳細](#5-runner-ipo-詳細)
- [6. 破壊的操作の承認（HITL CONFIRM）](#6-破壊的操作の承認hitl-confirm)
- [7. 変更履歴](#7-変更履歴)

---

## 概要

`backend/app/core/data_jobs.py` は、データ準備パイプライン
（チャンキング / Q/A 生成 / Qdrant 登録 / コレクション削除）の**ジョブ runner** である。

GRACE-Support・GRACE-Review と**同じジョブ基盤**（`core/jobs.py`）に乗せる。
`register_runner(params_type, runner, kind)` で params の型から runner を解決する
仕組みがすでにあるため、**`jobs.py` 側に手を入れずに** 4 種類を追加できる。

| params | kind | 実処理 |
|---|---|---|
| `ChunkingParams` | `chunking` | `chunking/csv_text_to_chunks_text_csv.py` |
| `QaGenerationParams` | `qa` | `qa_generation/pipeline.py::QAPipeline` |
| `RegisterParams` | `register` | `qa_qdrant/register_to_qdrant.py` |
| `DeleteParams` | `delete` | `services/data_pipeline_service.delete_collection` |

### 主な責務

- 4 種のジョブパラメータ（dataclass）を定義する
- 各 runner でステップを刻み、`step` / `log` / `error` イベントを出す
- 既存パッケージの `logging` 出力を `capture_logs()` で横取りして SSE へ流す
- 破壊的操作の前に HITL CONFIRM を通す

### 各責務対応のモジュール

| # | 責務 | 対応モジュール |
|---|------|--------------|
| 1 | ジョブ基盤への登録 | `core/jobs.py` :: `register_runner` |
| 2 | ログ横取り | `core/job_logs.py` :: `capture_logs` |
| 3 | HITL CONFIRM | `grace/intervention.py` :: `InterventionRequest` / `InterventionLevel` |
| 4 | イベント型 | `core/support_agent.py` :: `SupportEvent` / `EmitFn` / `ConfirmFn` |
| 5 | 実処理 | `chunking/` `qa_generation/` `qa_qdrant/` `services/data_pipeline_service.py` |

### 主要機能一覧

| 機能 | 説明 |
|------|------|
| `ChunkingParams` / `QaGenerationParams` / `RegisterParams` / `DeleteParams` | 4 種のジョブパラメータ |
| `CHUNKING_STEP_IDS` ほか 8 定数 | フロントの Timeline が使うステップ ID とラベル |
| `_make_emitters(emit)` | `log` / `step_started` / `step_finished` / `step_skipped` / `error` を作る |
| `_ask_confirmation(confirm, message, reason)` | HITL CONFIRM を要求し `(承認, タイムアウト)` を返す |
| `_chunking_runner` / `_qa_runner` / `_register_runner` / `_delete_runner` | 4 種の実処理 |

### 進捗の出し方

どのパッケージも進捗コールバックを持たないため、`core/job_logs.py` の
`capture_logs()` で `logging` 出力を横取りして SSE の log イベントへ流す
（**既存コードは無改修**）。ステップの区切りだけは runner 側で `step` イベントを出す。

---

## 1. アーキテクチャ構成図

```mermaid
flowchart TB
    subgraph API2["backend/app/api/data.py"]
        POST["POST /api/chunking/run ほか"]
    end

    subgraph JOBS["core/jobs.py"]
        JM["job_manager.start(params)"]
        REG["register_runner(型 → runner)"]
    end

    subgraph THIS["core/data_jobs.py"]
        CP["ChunkingParams"]
        QP["QaGenerationParams"]
        RP["RegisterParams"]
        DP["DeleteParams"]
        CR["_chunking_runner"]
        QR["_qa_runner"]
        RR["_register_runner"]
        DR["_delete_runner"]
        EMIT["_make_emitters()"]
        ASK["_ask_confirmation()"]
    end

    subgraph EXT2["実処理（無改修）"]
        CHUNKPKG["chunking/"]
        QAGPKG["qa_generation/"]
        QAQPKG["qa_qdrant/"]
        DPS2["services/data_pipeline_service.py"]
    end

    POST --> JM
    JM --> REG
    REG --> CR
    REG --> QR
    REG --> RR
    REG --> DR
    CP --> CR
    QP --> QR
    RP --> RR
    DP --> DR
    CR --> EMIT
    QR --> EMIT
    RR --> EMIT
    DR --> EMIT
    RR --> ASK
    DR --> ASK
    CR --> CHUNKPKG
    QR --> QAGPKG
    RR --> QAQPKG
    DR --> DPS2
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class POST,JM,REG,CP,QP,RP,DP,CR,QR,RR,DR,EMIT,ASK,CHUNKPKG,QAGPKG,QAQPKG,DPS2 default
style API2 fill:#1a1a1a,stroke:#fff,color:#fff
style JOBS fill:#1a1a1a,stroke:#fff,color:#fff
style THIS fill:#1a1a1a,stroke:#fff,color:#fff
style EXT2 fill:#1a1a1a,stroke:#fff,color:#fff
```

---

## 2. ステップ定義

フロントの Timeline が使う ID と **1:1** で対応する。
ID のタプル（`*_STEP_IDS`）とラベルの辞書（`*_STEP_LABELS`）を対で持つ。

| 定数 | 型 | 用途 |
|---|---|---|
| `CHUNKING_STEP_IDS` / `CHUNKING_STEP_LABELS` | `tuple[str, ...]` / `Dict[str, str]` | チャンキングの 3 段 |
| `QA_STEP_IDS` / `QA_STEP_LABELS` | 同上 | Q/A 生成の 4 段 |
| `REGISTER_STEP_IDS` / `REGISTER_STEP_LABELS` | 同上 | 登録の 4 段 |
| `DELETE_STEP_IDS` / `DELETE_STEP_LABELS` | 同上 | 削除の 3 段 |

runner は `step_started(id, LABELS[id], ...)` の形でラベルを引く。

### 2.1 チャンキング（`CHUNKING_STEP_IDS`）

| ID | ラベル |
|---|---|
| `load` | ① 入力読み込み（CSV / テキスト） |
| `chunk` | ② セマンティックチャンク化（LLM・3 段階） |
| `save` | ③ CSV 出力 |

### 2.2 Q/A 生成（`QA_STEP_IDS`）

| ID | ラベル |
|---|---|
| `load` | ① チャンク済み CSV の読み込み |
| `generate` | ② Q/A ペア生成（LLM） |
| `coverage` | ③ カバレージ分析（任意） |
| `save` | ④ Q/A CSV・JSON 出力 |

> 📝 `analyze_coverage=False` のとき `coverage` は **`step_skipped`** になる
> （無言で飛ばさない）。

### 2.3 登録（`REGISTER_STEP_IDS`）

| ID | ラベル |
|---|---|
| `prepare` | ① 入力検証・コレクション名の決定 |
| `confirm` | ② HITL CONFIRM（recreate 時のみ） |
| `embed` | ③ Embedding 生成 |
| `upsert` | ④ Qdrant へ登録 |

### 2.4 削除（`DELETE_STEP_IDS`）

| ID | ラベル |
|---|---|
| `inspect` | ① 削除対象の確認 |
| `confirm` | ② HITL CONFIRM（承認が必要） |
| `delete` | ③ 削除実行 |

---

## 3. クラス・関数一覧表

| 名前 | 種別 | 概要 |
|---|---|---|
| `ChunkingParams` | dataclass | `POST /api/chunking/run` のパラメータ（CLI 引数と 1:1） |
| `QaGenerationParams` | dataclass | `POST /api/qa/generate` のパラメータ |
| `RegisterParams` | dataclass | `POST /api/qdrant/register` のパラメータ |
| `DeleteParams` | dataclass | `POST /api/qdrant/delete` のパラメータ |
| `_make_emitters(emit)` | 関数 | `support_agent.py` と同じ形の step/log ヘルパを 5 つ返す |
| `_ask_confirmation(confirm, message, reason)` | 関数 | CONFIRM を要求し `(承認されたか, タイムアウトしたか)` を返す |
| `_chunking_runner(params, emit, confirm)` | runner | CSV / テキスト → セマンティックチャンク CSV |
| `_qa_runner(params, emit, confirm)` | runner | チャンク済み CSV → Q/A ペア CSV・JSON |
| `_register_runner(params, emit, confirm)` | runner | Q/A CSV → Qdrant コレクション |
| `_delete_runner(params, emit, confirm)` | runner | コレクション削除 |

---

## 4. パラメータ IPO 詳細

### 4.1 使用例

#### 4.1.1 基本的なワークフロー（パラメータとステップ定義）

4 種の runner は `params` の**型**で解決される（`register_runner()` 済み）。
呼び出し側が作るのはパラメータだけで、runner を直接呼ぶ必要はない。

```python
from backend.app.core.data_jobs import (
    ChunkingParams, DeleteParams, CHUNKING_STEP_IDS, DELETE_STEP_IDS,
)

# 1. チャンク化（非破壊なので CONFIRM なし）
p = ChunkingParams(input_file="OUTPUT/cc_news_1per.csv")
print(f"{type(p).__name__}: {p.input_file} -> {p.output_dir}")
print(f"steps: {CHUNKING_STEP_IDS}")

# 2. 削除（破壊的なので confirm ステップを持つ）
d = DeleteParams(collections=["demo_anthropic"])
print(f"{type(d).__name__}: {d.collections} / steps={DELETE_STEP_IDS}")

# 出力例:
# ChunkingParams: OUTPUT/cc_news_1per.csv -> output_chunked
# steps: ('load', 'chunk', 'save')
# DeleteParams: ['demo_anthropic'] / steps=('inspect', 'confirm', 'delete')
```

> ⚠️ **`confirm` ステップの有無が、そのジョブが破壊的かどうかを表す。**
> 削除は常に、登録は `recreate=True` のときだけ HITL CONFIRM を通る（§7）。

#### 4.1.2 ジョブとして起動する

```python
from backend.app.core.jobs import JobManager
from backend.app.core.data_jobs import ChunkingParams

mgr = JobManager()
job = mgr.start(ChunkingParams(input_file="OUTPUT/cc_news_1per.csv"))
# → params の型から _chunking_runner が解決される（kind="data"）
# → 進捗は job.stream_events() / GET /api/data/stream/{job_id} で購読する
```

> 実行には入力 CSV と（登録ジョブでは）Qdrant が要るため、ここでは起動までを示す。
> 画面から実行する手順は [`data_pipeline.md` §5](../data_pipeline.md#5-使用例)。


### 4.2 `ChunkingParams`

```python
@dataclass
class ChunkingParams:
    input_file: str                      # 'ディレクトリ名/ファイル名' 形式
    output_dir: str = "output_chunked"
    model: str = "claude-haiku-4-5"
    workers: int = 8
    block_size: int = 1000
    text_column: Optional[str] = None
    max_rows: Optional[int] = None
    combine_rows: bool = False
    resume: Optional[str] = None         # CheckpointManager の再開用ジョブ ID
    verbose: bool = False
```

> 📝 **CLI 引数と 1:1 対応**。`resume` は `--resume` 相当で、
> `CheckpointManager` の再開に使う。

### 4.3 `QaGenerationParams`

```python
@dataclass
class QaGenerationParams:
    input_file: str                      # 'ディレクトリ名/ファイル名' 形式
    output_dir: str = "qa_output"
    model: str = "claude-sonnet-5"
    max_docs: Optional[int] = None
    use_celery: bool = False
    concurrency: int = 8
    batch_chunks: int = 3
    analyze_coverage: bool = True
    verbose: bool = False
```

> 📝 入力は**チャンク済み CSV**。`text` / `Combined_Text` / `content` /
> `chunk_text` のいずれかのカラムが要る。

> ⚠️ **`output_dir` の既定を入れ子にしない。** `list_input_files()` は
> `iterdir()` でサブディレクトリを見ないため、`qa_output/pipeline` にすると
> 生成した Q/A CSV が「③ Qdrant 登録」の選択肢に出てこない。

> 📝 **モデルの既定はチャンク化（`claude-haiku-4-5`）と違う。** Q/A 生成は
> 文章生成の比重が大きいので、CLI（`make_qa_register_qdrant.py --model`）と
> `QAPipeline` の既定に合わせて `claude-sonnet-5` にしてある。

> ⚠️ **`use_celery=True` にするなら Celery ワーカーが起動していること。**
> 落ちているとパイプラインが例外を投げ、runner が error イベントへ変換する。

### 4.4 `RegisterParams`

```python
@dataclass
class RegisterParams:
    input_file: str
    collection: str
    recreate: bool = False               # ⚠️ True は破壊的。CONFIRM を通す
    batch_size: int = 100
    embed_workers: int = 2
    text_col: Optional[str] = None
    domain: Optional[str] = None
    max_docs: Optional[int] = None
    provider: str = "gemini"             # Embedding は Gemini
    normalize_filename: bool = True
    create_ui_csv: bool = True
    ui_output_dir: str = "qa_output"
    verbose: bool = False
```

> ⚠️ **`recreate=True` は既存コレクションを削除して作り直す ＝ 破壊的。** CONFIRM を通す。

> 📝 **`provider="gemini"` は正しい。** Embedding は Gemini（`gemini-embedding-001`・3072 次元）で、
> LLM 用途（Anthropic）とは別系統（CLAUDE.md §3 のプロバイダ方針）。

### 4.5 `DeleteParams`

```python
@dataclass
class DeleteParams:
    collections: List[str]
    verbose: bool = False
```

> ⚠️ **必ず CONFIRM を通る。**

---

## 5. runner IPO 詳細

### 5.1 `_make_emitters`

```python
def _make_emitters(emit: EmitFn)
```

| 項目 | 内容 |
|------|------|
| **Input** | `emit` |
| **Process** | クロージャで 5 つの関数を作る |
| **Output** | `(log, step_started, step_finished, step_skipped, error)` |

| 返る関数 | 送る `SupportEvent` |
|---|---|
| `log(message, step, **data)` | `type="log"` |
| `step_started(step, title, **data)` | `type="step"`, `status="started"` |
| `step_finished(step, **data)` | `type="step"`, `status="finished"` |
| `step_skipped(step, **data)` | `type="step"`, `status="skipped"` |
| `error(message, **data)` | `type="error"` |

> 📝 `support_agent.py` と**同じ形**にしてあるので、フロントの Timeline は
> Support / Review / データ準備を同じコードで描ける。

### 5.2 `_ask_confirmation`

```python
def _ask_confirmation(confirm: ConfirmFn, message: str, reason: str) -> tuple[bool, bool]
```

| 項目 | 内容 |
|------|------|
| **Input** | `confirm`、`message`（ユーザーに見せる文）、`reason` |
| **Process** | `confirm(InterventionRequest(level=CONFIRM, message=..., reason=...))` |
| **Output** | `(response.should_continue, response.timeout_reached)` |

> 📝 **`confirm` が `None` のケースは呼び出し側で潰してある**（Web は必ず
> `InterventionBridge.resolver` が渡る）。CLI から使う場合は呼び出し側で
> `confirm or ...` を用意すること。

### 5.3 `_chunking_runner`

| 項目 | 内容 |
|------|------|
| **Input** | `ChunkingParams`、`emit`、`confirm`（**使わない**） |
| **Process** | ① `ANTHROPIC_API_KEY` が無ければ error して終了 ② `load`: `resolve_input_file()` → `capture_logs(step="load")` の中で `load_input_text()`。空なら error ③ `chunk`: `generate_output_filename()` で出力先を決め、`capture_logs(step="chunk")` の中で `run_chunking_sync()` ④ `save`: 出力ファイルの存在を確認（無ければ警告ログ） |
| **Output** | `{"kind": "chunking", "input_file", "output_file", "chunks", "chars", "model"}`（失敗時は `None`） |

> 📝 **`confirm` は使わない。** チャンク化は既存データを壊さないため承認不要。
> 出力ファイルが既にあっても、**CLI と同じく上書きする**。

> ⚠️ **`ChunkingAbortedError` は他の例外と分けて捕まえる。** LLM 呼び出しが
> 連続で失敗して中断した場合で、原因と対処はメッセージ側が持っている。
> `type(e).__name__` を前置きすると読みにくくなるだけなので、そのまま出す。
> 詳細は [`chunking/docs/async_api_client.md`](../../../chunking/docs/async_api_client.md) §4.4。

### 5.4 `_qa_runner`

| 項目 | 内容 |
|------|------|
| **Input** | `QaGenerationParams`、`emit`、`confirm`（**使わない**） |
| **Process** | ① `ANTHROPIC_API_KEY` が無ければ error して終了 ② `load`: `resolve_input_file()` → 拡張子（`.csv`）とテキストカラムを検証 ③ `generate`: `capture_logs(step="generate")` の中で `run_qa_generation_sync()`。終わったら `handler.set_step()` で以降のログを次段へ寄せる。**0 件なら error** ④ `coverage`: 結果の `coverage_results` を出す（`analyze_coverage=False` なら skip） ⑤ `save`: 出力ファイルの存在を確認 |
| **Output** | `{"kind": "qa", "input_file", "qa_csv", "qa_json", "qa_count", "coverage_rate", "total_chunks", "model"}`（失敗時は `None`） |

> 📝 **`confirm` は使わない。** Q/A 生成は既存データを壊さない。出力は
> タイムスタンプ付きの新規ファイルなので、既存の Q/A CSV も消えない。

> ⚠️ **入力の誤りは ① で返す。** テキストカラムの検証を `QAPipeline` 任せに
> すると、`ValueError` が**生成ステップの失敗**として見えてしまう。
> LLM を呼ぶ前に分かる誤りなので `pd.read_csv(nrows=1)` で先に確かめる。

> ⚠️ **`qa_count == 0` は成功にしない。** 例外が出ていなくても、そのまま通すと
> 後続の Qdrant 登録が空のファイルを掴んで空振りする。

### 5.5 `_register_runner`

| 項目 | 内容 |
|------|------|
| **Input** | `RegisterParams`、`emit`、`confirm` |
| **Process** | ① `prepare`: `resolve_input_file()` → Qdrant へ接続し `collection_exists()` と既存件数を取る（接続失敗は起動コマンド入りの error） ② `confirm`: **`recreate=True` かつ既存があるときだけ** `_ask_confirmation()`。承認されなければ `cancelled: True` で返す（既存データは維持）。それ以外は `step_skipped` ③ `embed`: `capture_logs(step="embed")` の中で `register_to_qdrant()` を呼び、途中で `handler.set_step("upsert")` ④ `upsert`: 登録後の件数を確認（取得失敗は警告に留める） |
| **Output** | `{"kind": "register", "collection", "input_file", ...}`（失敗時は `None`、中止時は `cancelled: True`） |

> 📝 **`embed` と `upsert` は `register_to_qdrant()` が両方やる。**
> ステップの切り替えは `capture_logs()` が返すハンドラの `set_step()` で行う。

> 📝 **登録後の件数取得に失敗しても error にしない。** 登録自体は成功しているため、
> 警告ログに留める。

### 5.6 `_delete_runner`

| 項目 | 内容 |
|------|------|
| **Input** | `DeleteParams`、`emit`、`confirm` |
| **Process** | ① 対象が空なら error ② `inspect`: 全コレクションを引き、存在するものを `targets`、しないものを `missing` に分ける。合計件数を出す。`targets` が空なら error ③ `confirm`: **常に** `_ask_confirmation()`。承認されなければ `cancelled: True` で返す ④ `delete`: `capture_logs(step="delete")` の中で `delete_collection()` を 1 件ずつ呼び、`deleted` / `failed` に振り分ける |
| **Output** | `{"kind": "delete", "deleted", "failed", "missing", "cancelled", "total_points"}` |

> ⚠️ **単発の `DELETE` エンドポイントにしていない。**
> 誤操作で不可逆に消えるのを防ぐため。承認画面には**対象名と件数**を出す
> （「合計 N 件のデータが失われ、元に戻せません」）。

> 📝 **存在しないコレクションは `missing` として扱い、処理は続ける。**
> 指定の一部が既に消えていても、残りは削除できる。

---

## 6. 破壊的操作の承認（HITL CONFIRM）

| 操作 | 承認 | 理由 |
|---|---|---|
| チャンク化 | **なし** | 既存データを壊さない |
| Q/A 生成 | **なし** | 出力はタイムスタンプ付きの新規ファイル。既存の Q/A CSV も残る |
| 登録（`recreate=False`） | なし | 追記のみ |
| 登録（`recreate=True`） | **あり** | 既存コレクションを削除して作り直す |
| 削除 | **常にあり** | 不可逆 |

> 📝 **登録で毎回ダイアログを出さない理由。** 煩わしいため、**破壊を伴う場合に限定**する。

承認は Support / Review と同じ `InterventionBridge` を通るので、フロントは既存の
`ConfirmModal` をそのまま使える。**タイムアウト時は実行しない**（安全側）。

### runner の登録

```python
# この import 時点で jobs.py に効く
register_runner(ChunkingParams, _chunking_runner, "chunking")
register_runner(QaGenerationParams, _qa_runner, "qa")
register_runner(RegisterParams, _register_runner, "register")
register_runner(DeleteParams,   _delete_runner,   "delete")
```

> ⚠️ **モジュール末尾の副作用。** `api/data.py` はパラメータ型を使うために必ず
> このモジュールを import するので、**登録漏れは構造的に起きない**
> （`review_agent.py` と同じ方式）。

---

## 7. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.4 | 2026-09-16 | 3 階建て再編（`reference/` へ移設）に伴い、冒頭へ**位置づけと上位文書への導線**を追加した |
| 1.3 | **§4.1「使用例」を新設**（2026-09-15）。ドキュメント規約 `a_class_method_md_format.md` §6.1 が IPO 詳細セクションの冒頭に必須としている代表ワークフローが欠落していた。パラメータとステップ定義（confirm ステップの有無が破壊性を表す）、ジョブとしての起動の 2 本を追加し、**実行して出力を確認した**（外部依存が要る例はその旨を明記）。旧 §4.1〜§4.4 は §4.2〜§4.5 へ繰り下げ |
| 1.0 | 初版作成。`backend/app/core/data_jobs.py`（547 行）の全公開要素を IPO 形式で記述。3 種のステップ定義、`jobs.py` に手を入れず `register_runner` で追加する方式、既存 3 パッケージを無改修のまま `capture_logs()` で進捗を出す方式、CONFIRM の要否（削除は常に／登録は `recreate=True` のときだけ）とその理由、`provider="gemini"` が Embedding 用途として正しいことを実コードのコメントから起こして記載 |
| 1.1 | **Q/A 生成を追加**（`QaGenerationParams` / `_qa_runner` / `QA_STEP_IDS`）。runner は 4 種になった。出力先の既定を `qa_output` 直下にした理由（`list_input_files()` が非再帰）、入力検証を ① で完結させる理由、0 件生成を error にする理由を追記。§2・§4・§5 の節番号を繰り下げ |
| 1.2 | `_chunking_runner` が `ChunkingAbortedError` を専用に捕捉するようになったことを追記。LLM が連続で失敗したとき、機械的分割へフォールバックして「成功」で終わらせないための中断（回帰は `test_chunking_abort.py`） |
