# backend/app/schemas.py
"""API のリクエスト/レスポンス/イベントの Pydantic スキーマ。

`SupportResult`（backend/app/core/support_agent.py の dataclass）を JSON 化した
ものが `SupportResultModel`。ステップ進捗は SSE（GET /api/support/stream/{job_id}）
で `SupportEventModel` 形式の JSON として逐次配信される。
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """POST /api/support/query（CLI 引数と 1:1 対応）。"""

    query: str = Field(min_length=1, description="問い合わせ内容（チャット入力）")
    vertical: Optional[Literal["gov", "saas", "ec"]] = Field(
        default=None, description="業界プロファイル（--vertical 相当）")
    dry_run: bool = Field(default=True, description="アクションのドライラン（既定 ON）")
    use_web: bool = Field(default=True, description="Web フォールバック（--no-web 相当の逆）")
    do_action: bool = Field(default=True, description="アクション実行（--no-action 相当の逆）")
    verbose: bool = Field(default=False, description="詳細ログ（-v 相当）")


class QueryAccepted(BaseModel):
    """ジョブ受付レスポンス。"""

    job_id: str
    stream_url: str


class ConfirmRequest(BaseModel):
    """POST /api/support/confirm/{job_id}（HITL CONFIRM への応答）。"""

    intervention_id: str
    approve: bool


class ConfirmResponse(BaseModel):
    status: Literal["resolved", "not_found", "not_waiting"]


class ActionRequestModel(BaseModel):
    action_type: str
    args: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = True


class SupportResultModel(BaseModel):
    """`SupportResult` の JSON 表現（GET /api/support/result/{job_id}）。"""

    answer: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    groundedness: float = 0.0
    groundedness_decided: int = 0
    decision: Literal["answer", "escalate"] = "escalate"
    warning: bool = False
    used_web: bool = False
    source_agreement: Optional[float] = None
    contradiction: bool = False
    action: Optional[ActionRequestModel] = None
    action_result: Optional[str] = None
    vertical: Optional[str] = None
    overall_confidence: float = 0.0
    intent: Optional[str] = None
    forced_escalate: bool = False
    identity_checked: bool = False
    no_info_detected: bool = False
    web_reused: bool = False


class JobStatusResponse(BaseModel):
    """GET /api/support/result/{job_id}。"""

    job_id: str
    status: Literal["running", "completed", "failed"]
    result: Optional[SupportResultModel] = None


class SupportEventModel(BaseModel):
    """SSE で配信される進捗イベント（core.SupportEvent ＋ 通し番号/時刻）。"""

    seq: int
    ts: float
    type: Literal["step", "log", "intervention", "result", "error"]
    step: Optional[str] = None
    status: Optional[str] = None
    title: str = ""
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class VerticalInfo(BaseModel):
    """GET /api/verticals の 1 要素。"""

    id: str
    name: str
    collections: List[str]
    escalate_keywords: List[str]
    action_map: Dict[str, str]
    require_identity: bool
    notify_th: Optional[float] = None
    confirm_th: Optional[float] = None
    prompt_addendum: str = ""
