# backend/app/api/meta.py
"""メタ情報 API（業界プロファイル一覧・ヘルスチェック）。"""
from __future__ import annotations

import os
from typing import Dict, List

from fastapi import APIRouter

from backend.app.core.verticals import PROFILES
from backend.app.schemas import VerticalInfo

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/verticals", response_model=List[VerticalInfo])
def list_verticals() -> List[VerticalInfo]:
    """UI のプロファイルセレクタ用に、組み込み業界プロファイルを返す。"""
    return [
        VerticalInfo(
            id=key,
            name=profile.name,
            collections=list(profile.collections),
            escalate_keywords=list(profile.escalate_keywords),
            action_map=dict(profile.action_map),
            require_identity=profile.require_identity,
            notify_th=profile.notify_th,
            confirm_th=profile.confirm_th,
            prompt_addendum=profile.prompt_addendum,
        )
        for key, profile in PROFILES.items()
    ]


@router.get("/health")
def health() -> Dict[str, object]:
    """稼働確認と実行前提（APIキー設定有無）の可視化。"""
    return {
        "status": "ok",
        "anthropic_api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google_api_key": bool(os.getenv("GOOGLE_API_KEY")),
    }
