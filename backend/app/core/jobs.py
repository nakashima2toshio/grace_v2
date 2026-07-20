# backend/app/core/jobs.py
"""サポート問い合わせのジョブ管理（インメモリ）。

1 クエリ = 1 ジョブ。ジョブはワーカースレッドで `run_support_agent_core` を実行し、
進捗イベントを蓄積する。SSE 購読者はイベント列を先頭から追いかける
（再接続・途中購読でも全イベントをリプレイできる）。ローカル開発用の
シングルプロセス前提で、永続化はしない。
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from backend.app.core.intervention_bridge import InterventionBridge
from backend.app.core.support_agent import (
    SupportEvent,
    result_to_dict,
    run_support_agent_core,
)

logger = logging.getLogger(__name__)

# 完了済みジョブをメモリに保持する上限（超えたら古い完了ジョブから破棄）
MAX_FINISHED_JOBS = 50


@dataclass
class JobParams:
    """POST /api/support/query のパラメータ（CLI 引数と 1:1 対応）。"""

    query: str
    vertical: Optional[str] = None
    dry_run: bool = True
    use_web: bool = True
    do_action: bool = True
    verbose: bool = False


@dataclass
class SupportJob:
    """実行中/完了のジョブ。イベント列と最終結果を保持する。"""

    job_id: str
    params: JobParams
    status: str = "running"            # running / completed / failed
    events: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    cond: threading.Condition = field(default_factory=threading.Condition)
    bridge: Optional[InterventionBridge] = None

    def emit(self, event: SupportEvent) -> None:
        """コアからの進捗イベントを蓄積し、SSE 購読者を起こす。"""
        record = {"seq": len(self.events), "ts": time.time(), **asdict(event)}
        with self.cond:
            self.events.append(record)
            self.cond.notify_all()

    def finish(self, status: str, result: Optional[Dict[str, Any]] = None) -> None:
        with self.cond:
            self.status = status
            self.result = result
            self.finished_at = time.time()
            self.cond.notify_all()

    @property
    def done(self) -> bool:
        return self.status != "running"

    def stream_events(self, poll_timeout: float = 15.0) -> Iterator[Optional[Dict[str, Any]]]:
        """イベントを先頭から順に返すブロッキングイテレータ。

        新イベントが `poll_timeout` 秒来ない場合は None を返す
        （SSE 側は keepalive コメントを送って接続維持する）。
        ジョブ完了かつ全イベント配信済みで終了する。
        """
        index = 0
        while True:
            with self.cond:
                if index >= len(self.events) and not self.done:
                    self.cond.wait(timeout=poll_timeout)
                if index < len(self.events):
                    event = self.events[index]
                    index += 1
                else:
                    if self.done:
                        return
                    event = None  # タイムアウト → keepalive
            yield event


class JobManager:
    """ジョブの生成・参照・HITL 応答の注入を担う（インメモリ・スレッドセーフ）。"""

    def __init__(self):
        self._jobs: Dict[str, SupportJob] = {}
        self._lock = threading.Lock()

    def start(self, params: JobParams) -> SupportJob:
        job = SupportJob(job_id=uuid.uuid4().hex[:12], params=params)
        job.bridge = InterventionBridge(emit=job.emit)
        with self._lock:
            self._gc_finished_locked()
            self._jobs[job.job_id] = job
        thread = threading.Thread(
            target=self._run, args=(job,), name=f"support-job-{job.job_id}", daemon=True
        )
        thread.start()
        return job

    def get(self, job_id: str) -> Optional[SupportJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def confirm(self, job_id: str, intervention_id: str, approve: bool) -> str:
        """HITL 応答を注入する。戻り値: "resolved" / "not_found" / "not_waiting"。"""
        job = self.get(job_id)
        if job is None:
            return "not_found"
        if job.bridge is None or not job.bridge.resolve(intervention_id, approve):
            return "not_waiting"
        return "resolved"

    def _run(self, job: SupportJob) -> None:
        p = job.params
        try:
            result = run_support_agent_core(
                p.query,
                verbose=p.verbose,
                use_web=p.use_web,
                do_action=p.do_action,
                dry_run=p.dry_run,
                vertical=p.vertical,
                identity=None,
                emit=job.emit,
                confirm=job.bridge.resolver,
            )
        except Exception as e:  # Qdrant 未起動・LLM タイムアウト等をイベントで配信
            logger.exception(f"support job {job.job_id} failed")
            job.emit(SupportEvent(
                type="error",
                message=f"❌ 実行に失敗しました: {type(e).__name__}: {e}",
                data={"hint": "Qdrant の起動と .env の API キーを確認してください。"},
            ))
            job.finish("failed")
            return
        if result is None:  # APIキー未設定（error イベントは emit 済み）
            job.finish("failed")
        else:
            job.finish("completed", result_to_dict(result))

    def _gc_finished_locked(self) -> None:
        """完了ジョブが増えすぎたら古い順に破棄する（呼び出し側で lock 保持）。"""
        finished = sorted(
            (j for j in self._jobs.values() if j.done),
            key=lambda j: j.finished_at or 0,
        )
        for job in finished[: max(0, len(finished) - MAX_FINISHED_JOBS)]:
            self._jobs.pop(job.job_id, None)


# アプリ全体で共有するシングルトン（ローカル・シングルプロセス前提）
job_manager = JobManager()
