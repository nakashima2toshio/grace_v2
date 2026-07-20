# core/jobs.py - ジョブ管理（インメモリ）ドキュメント

**Version 1.0** | 最終更新: 2026-07-15

---

## 目次

1. [概要](#概要)
2. [アーキテクチャ構成図](#1-アーキテクチャ構成図)
3. [モジュール構成図](#2-モジュール構成図)
4. [クラス・関数一覧表](#3-クラス関数一覧表)
5. [クラス・関数 IPO詳細](#4-クラス関数-ipo詳細)
6. [設定・定数](#5-設定定数)
7. [使用例](#6-使用例)
8. [エクスポート](#7-エクスポート)
9. [変更履歴](#8-変更履歴)
10. [付録: 依存関係図](#付録-依存関係図)

---

## 概要

`backend/app/core/jobs.py` は、GRACE-Support の**サポート問い合わせのジョブ管理（インメモリ）**を
担うモジュール。1 クエリ = 1 ジョブとし、ジョブはワーカースレッドで `run_support_agent_core` を
実行して進捗イベントを蓄積する。SSE 購読者はイベント列を先頭から追いかけるため、再接続・
途中購読でも全イベントをリプレイできる。

ローカル開発用のシングルプロセス前提で、永続化はしない。完了ジョブは `MAX_FINISHED_JOBS`
上限で古い順に破棄する。HITL CONFIRM は `InterventionBridge` を介して非同期に解決する。

### 主な責務

- ジョブの生成・ワーカースレッド起動（`JobManager.start`）
- 進捗イベントの蓄積と SSE 購読者への通知（`SupportJob.emit` / `stream_events`）
- 最終結果・状態の保持（running / completed / failed）
- HITL CONFIRM 応答の注入（`JobManager.confirm` → `InterventionBridge.resolve`）
- 完了ジョブの GC（`MAX_FINISHED_JOBS` 超過分を破棄）

### 各責務対応のモジュール

| # | 責務 | 対応モジュール | 説明 |
|---|------|--------------|------|
| 1 | ジョブ生成・実行 | `jobs.py`（`JobManager`） | ワーカースレッドで core を実行 |
| 2 | イベント蓄積/配信 | `jobs.py`（`SupportJob`） | `emit` / `stream_events` |
| 3 | HITL 応答注入 | `core/intervention_bridge.py` | `InterventionBridge.resolve` |
| 4 | コア実行 | `core/support_agent.py` | `run_support_agent_core` |

### 主要機能一覧

| 機能 | 説明 |
|------|------|
| `JobParams` | クエリパラメータ（CLI 引数と 1:1） |
| `SupportJob` | 実行中/完了のジョブ（イベント列＋結果） |
| `SupportJob.emit()` | 進捗イベントを蓄積し購読者を起こす |
| `SupportJob.finish()` | 状態と結果を確定 |
| `SupportJob.stream_events()` | イベントを先頭から返すブロッキングイテレータ |
| `JobManager` | ジョブの生成・参照・HITL 注入 |
| `JobManager.start()` | ジョブを起動 |
| `JobManager.get()` | ジョブを参照 |
| `JobManager.confirm()` | HITL 応答を注入 |
| `job_manager` | アプリ全体で共有するシングルトン |

---

## 1. アーキテクチャ構成図

### 1.1 システム全体構成

```mermaid
flowchart TB
    subgraph CLIENT["クライアント層"]
        API["api/support.py（4 エンドポイント）"]
    end

    subgraph MODULE["core/jobs.py"]
        JM["JobManager（シングルトン job_manager）"]
        SJ["SupportJob（イベント列＋結果）"]
        JP["JobParams"]
    end

    subgraph CORE["コア・ブリッジ"]
        AGENT["run_support_agent_core()"]
        BRIDGE["InterventionBridge"]
    end

    API --> JM
    JM --> SJ
    JM --> JP
    SJ --> AGENT
    SJ --> BRIDGE
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class API,JM,SJ,JP,AGENT,BRIDGE default
style CLIENT fill:#1a1a1a,stroke:#fff,color:#fff
style MODULE fill:#1a1a1a,stroke:#fff,color:#fff
style CORE fill:#1a1a1a,stroke:#fff,color:#fff
```

### 1.2 データフロー

1. `JobManager.start(params)` が `SupportJob` と `InterventionBridge` を生成、ワーカースレッド起動
2. ワーカーが `run_support_agent_core(..., emit=job.emit, confirm=bridge.resolver)` を実行
3. `emit` で蓄積されたイベントを `stream_events()` が SSE 購読者へ順に返す
4. CONFIRM 到達時、`JobManager.confirm()` → `bridge.resolve()` で応答を注入
5. 完了時 `finish("completed", result_to_dict(result))`、例外時 error イベント＋`finish("failed")`

---

## 2. モジュール構成図

### 2.1 内部モジュール構成

```mermaid
flowchart TB
    subgraph CONST["定数"]
        MFJ["MAX_FINISHED_JOBS"]
    end

    subgraph DATA["データ"]
        JP["JobParams"]
        SJ["SupportJob（emit/finish/stream_events/done）"]
    end

    subgraph MANAGER["JobManager"]
        ST["start()"]
        GET["get()"]
        CONF["confirm()"]
        RUN["_run()"]
        GC["_gc_finished_locked()"]
    end

    ST --> SJ
    ST --> RUN
    RUN --> SJ
    CONF --> SJ
    MFJ --> GC
    ST --> GC
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class MFJ,JP,SJ,ST,GET,CONF,RUN,GC default
style CONST fill:#1a1a1a,stroke:#fff,color:#fff
style DATA fill:#1a1a1a,stroke:#fff,color:#fff
style MANAGER fill:#1a1a1a,stroke:#fff,color:#fff
```

### 2.2 外部依存関係

| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| `threading` | 標準 | ワーカースレッド・`Condition` / `Lock` |
| `uuid` | 標準 | ジョブ ID 生成 |
| `time` | 標準 | 生成/完了時刻・イベント ts |
| `dataclasses` | 標準 | `JobParams` / `SupportJob` |
| `logging` | 標準 | 実行失敗のログ |

### 2.3 内部依存モジュール

| モジュール | 用途 |
|-----------|------|
| `backend.app.core.intervention_bridge` | `InterventionBridge`（HITL 非同期解決） |
| `backend.app.core.support_agent` | `SupportEvent` / `result_to_dict` / `run_support_agent_core` |

---

## 3. クラス・関数一覧表

### 3.1 クラス一覧

#### JobParams（dataclass）

| メソッド | 概要 |
|---------|------|
| （dataclass） | query / vertical / dry_run / use_web / do_action / verbose |

#### SupportJob（dataclass）

| メソッド | 概要 |
|---------|------|
| `emit(event)` | 進捗イベントを蓄積し購読者を起こす |
| `finish(status, result)` | 状態と結果を確定 |
| `done`（property） | running でなければ True |
| `stream_events(poll_timeout)` | イベントを先頭から返すブロッキングイテレータ |

#### JobManager

| メソッド | 概要 |
|---------|------|
| `__init__()` | ジョブ辞書とロックを初期化 |
| `start(params)` | ジョブを起動 |
| `get(job_id)` | ジョブを参照 |
| `confirm(job_id, intervention_id, approve)` | HITL 応答を注入 |
| `_run(job)` | ワーカー本体（core 実行） |
| `_gc_finished_locked()` | 完了ジョブの GC |

### 3.2 関数一覧

モジュールレベル関数はない（`job_manager` はシングルトンインスタンス）。

---

## 4. クラス・関数 IPO詳細

### 4.1 JobParams クラス

**概要**: `POST /api/support/query` のパラメータ（CLI 引数と 1:1）。

```python
JobParams(
    query: str,
    vertical: Optional[str] = None,
    dry_run: bool = True,
    use_web: bool = True,
    do_action: bool = True,
    verbose: bool = False,
)
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `query` | str | - | 問い合わせ内容 |
| `vertical` | Optional[str] | None | 業界プロファイル |
| `dry_run` / `use_web` / `do_action` | bool | True | ドライラン／Web／アクション |
| `verbose` | bool | False | 詳細ログ |

| 項目 | 内容 |
|------|------|
| **Input** | 上記フィールド |
| **Process** | 値を保持 |
| **Output** | `JobParams` |

**戻り値例**:
```python
JobParams(query="返品したい", vertical="ec", dry_run=True)
```

```python
# 使用例
job = job_manager.start(JobParams(query="返品したい", vertical="ec"))
```

### 4.2 SupportJob クラス

実行中/完了のジョブ。イベント列と最終結果を保持し、`threading.Condition` で購読者を通知する。

#### メソッド: `emit`

**概要**: コアからの進捗イベントを蓄積し、SSE 購読者を起こす。

```python
def emit(self, event: SupportEvent) -> None
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `event` | SupportEvent | - | コアが発行した進捗イベント |

| 項目 | 内容 |
|------|------|
| **Input** | `event: SupportEvent` |
| **Process** | 1. `{seq, ts, **asdict(event)}` の record を作成<br>2. Condition ロック下で `events` に append し `notify_all()` |
| **Output** | `None`（`events` に追記する副作用） |

**戻り値例**:
```python
# events に追加される record
{"seq": 3, "ts": 1752543210.1, "type": "log", "step": "gate", "message": "…", "data": {}}
```

```python
# 使用例（core へ渡す）
run_support_agent_core(..., emit=job.emit)
```

#### メソッド: `finish`

**概要**: ジョブの状態と結果を確定し、購読者を起こす。

```python
def finish(self, status: str, result: Optional[Dict[str, Any]] = None) -> None
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `status` | str | - | completed / failed |
| `result` | Optional[Dict[str, Any]] | None | 最終結果（dict） |

| 項目 | 内容 |
|------|------|
| **Input** | `status`, `result` |
| **Process** | Condition ロック下で status/result/finished_at を設定し `notify_all()` |
| **Output** | `None` |

**戻り値例**:
```python
# job.status = "completed", job.result = {...}
```

```python
# 使用例
job.finish("completed", result_to_dict(result))
```

#### メソッド: `stream_events`

**概要**: イベントを先頭から順に返すブロッキングイテレータ。新イベントが `poll_timeout` 秒
来ない場合は None（SSE 側は keepalive）。ジョブ完了かつ全イベント配信済みで終了。

```python
def stream_events(self, poll_timeout: float = 15.0) -> Iterator[Optional[Dict[str, Any]]]
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `poll_timeout` | float | 15.0 | 新イベント待ちタイムアウト（秒） |

| 項目 | 内容 |
|------|------|
| **Input** | `poll_timeout` |
| **Process** | index を進めつつ、未配信イベントがあれば yield、無く未完了なら wait、完了かつ配信済みで return、タイムアウトは None を yield |
| **Output** | `Iterator[Optional[Dict[str, Any]]]`: イベント dict または None（keepalive） |

**戻り値例**:
```python
{"seq": 0, "ts": ..., "type": "step", "step": "plan", "status": "started"}
None  # poll_timeout 到達 → keepalive
```

```python
# 使用例（api/support.py）
for event in job.stream_events():
    yield ": keepalive\n\n" if event is None else f"data: {json.dumps(event)}\n\n"
```

#### プロパティ: `done`

**概要**: ジョブが終了状態（running 以外）なら True。

```python
@property
def done(self) -> bool
```

| 項目 | 内容 |
|------|------|
| **Input** | なし（self のみ） |
| **Process** | `self.status != "running"` |
| **Output** | `bool` |

**戻り値例**:
```python
True   # completed / failed
False  # running
```

```python
# 使用例
if job.done: ...
```

### 4.3 JobManager クラス

ジョブの生成・参照・HITL 応答の注入を担う（インメモリ・スレッドセーフ）。

#### コンストラクタ: `__init__`

**概要**: ジョブ辞書とロックを初期化する。

```python
JobManager()
```

| 項目 | 内容 |
|------|------|
| **Input** | なし |
| **Process** | `self._jobs = {}`, `self._lock = threading.Lock()` |
| **Output** | `JobManager` インスタンス |

**戻り値例**:
```python
# 内部状態: _jobs={}, _lock=<Lock>
```

```python
# 使用例
job_manager = JobManager()  # モジュール末尾でシングルトン化
```

#### メソッド: `start`

**概要**: ジョブを生成し、ワーカースレッドで実行を開始する。

```python
def start(self, params: JobParams) -> SupportJob
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `params` | JobParams | - | クエリパラメータ |

| 項目 | 内容 |
|------|------|
| **Input** | `params` |
| **Process** | 1. `SupportJob`（job_id=uuid 12桁）生成、`bridge=InterventionBridge(emit=job.emit)`<br>2. ロック下で GC ＋ `_jobs` 登録<br>3. daemon スレッドで `_run(job)` 起動 |
| **Output** | `SupportJob`: 起動済みジョブ |

**戻り値例**:
```python
SupportJob(job_id="a1b2c3d4e5f6", status="running", ...)
```

```python
# 使用例
job = job_manager.start(JobParams(query="返品したい", vertical="ec"))
```

#### メソッド: `get`

**概要**: ジョブ ID からジョブを参照する（無ければ None）。

```python
def get(self, job_id: str) -> Optional[SupportJob]
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `job_id` | str | - | ジョブ ID |

| 項目 | 内容 |
|------|------|
| **Input** | `job_id` |
| **Process** | ロック下で `_jobs.get(job_id)` |
| **Output** | `Optional[SupportJob]` |

**戻り値例**:
```python
SupportJob(job_id="a1b2c3d4e5f6", status="completed", ...)  # または None
```

```python
# 使用例
job = job_manager.get(job_id)
```

#### メソッド: `confirm`

**概要**: HITL 応答を注入する。戻り値は resolved / not_found / not_waiting。

```python
def confirm(self, job_id: str, intervention_id: str, approve: bool) -> str
```

| パラメータ | 型 | デフォルト | 説明 |
|------------|------|-----------|------|
| `job_id` | str | - | ジョブ ID |
| `intervention_id` | str | - | 対象 intervention ID |
| `approve` | bool | - | 承認/拒否 |

| 項目 | 内容 |
|------|------|
| **Input** | `job_id`, `intervention_id`, `approve` |
| **Process** | 1. `get(job_id)`、無ければ `not_found`<br>2. `bridge.resolve(intervention_id, approve)` 失敗なら `not_waiting`<br>3. 成功で `resolved` |
| **Output** | `str`: "resolved" / "not_found" / "not_waiting" |

**戻り値例**:
```python
"resolved"
```

```python
# 使用例
status = job_manager.confirm(job_id, intervention_id, approve=True)
```

---

## 5. 設定・定数

### 5.1 MAX_FINISHED_JOBS

```python
MAX_FINISHED_JOBS = 50
```

| 定数名 | 値 | 説明 |
|-------|----|------|
| `MAX_FINISHED_JOBS` | 50 | メモリに保持する完了ジョブ数の上限。超えた分は `finished_at` の古い順に破棄 |

---

## 6. 使用例

### 6.1 基本的なワークフロー

```python
from backend.app.core.jobs import JobParams, job_manager

# 起動
job = job_manager.start(JobParams(query="返品したい", vertical="ec"))

# 進捗（SSE 側で消費）
for event in job.stream_events():
    ...  # None は keepalive

# HITL 応答
job_manager.confirm(job.job_id, intervention_id="9f8e...", approve=True)

# 結果参照
j = job_manager.get(job.job_id)
print(j.status, j.result)
```

---

## 7. エクスポート

`__all__` 定義はない。`api/support.py` が `JobParams` / `job_manager` を import する。

```python
# 公開シンボル（明示的 __all__ はなし）
JobParams, SupportJob, JobManager, job_manager, MAX_FINISHED_JOBS
```

---

## 8. 変更履歴

| バージョン | 変更内容 |
|-----------|---------|
| 1.0 | 初版作成（JobParams / SupportJob / JobManager / job_manager の IPO ドキュメント） |

---

## 付録: 依存関係図

```mermaid
flowchart LR
    JOBS["core/jobs.py"]

    subgraph STD["標準ライブラリ"]
        TH["threading"]
        UU["uuid"]
        TM["time"]
        DC["dataclasses"]
        LG["logging"]
    end

    subgraph INTERNAL["backend.app.core"]
        BRIDGE["intervention_bridge（InterventionBridge）"]
        AGENT["support_agent（SupportEvent / result_to_dict / run_support_agent_core）"]
    end

    JOBS --> TH
    JOBS --> UU
    JOBS --> TM
    JOBS --> DC
    JOBS --> LG
    JOBS --> BRIDGE
    JOBS --> AGENT
classDef default fill:#000,stroke:#fff,color:#fff
classDef subgraphStyle fill:#1a1a1a,stroke:#fff,color:#fff
class JOBS,TH,UU,TM,DC,LG,BRIDGE,AGENT default
style STD fill:#1a1a1a,stroke:#fff,color:#fff
style INTERNAL fill:#1a1a1a,stroke:#fff,color:#fff
```
