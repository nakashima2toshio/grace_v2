# backend/app/api/meta.py
"""メタ情報 API（業界プロファイル一覧・ルールセット一覧・ヘルスチェック）。"""
from __future__ import annotations

import os
from typing import Dict, List

from fastapi import APIRouter

from backend.app.core.rulesets import RULESETS
from backend.app.core.verticals import PROFILES
from backend.app.schemas import (
    ChunkingRequest,
    ModelChoice,
    ModelInfo,
    QaGenerationRequest,
    RuleSetInfo,
    VerticalInfo,
)
from config import ModelConfig, get_selectable_models
from grace.config import get_config

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/models", response_model=List[ModelChoice])
def list_models() -> List[ModelChoice]:
    """ヘッダーのモデルセレクタ用の選択肢一覧を返す。

    `config.py::get_selectable_models()` で絞り込み済み（旧既定・日付指定
    エイリアスは含まない）。単価と上限も添えて、選択の判断材料にする。

    ⚠️ Embedding はここに出ない。Embedding は Gemini（`ModelConfig.EMBEDDING_MODEL`）
    固定で、変更すると既存 Qdrant コレクションが使えなくなる（全件再登録）。
    """
    return [
        ModelChoice(
            id=m,
            input_price=ModelConfig.get_model_pricing(m)["input"],
            output_price=ModelConfig.get_model_pricing(m)["output"],
            context_window=ModelConfig.get_model_limits(m)["max_tokens"],
            max_output=ModelConfig.get_model_limits(m)["max_output"],
        )
        for m in get_selectable_models()
    ]


@router.get("/model", response_model=ModelInfo)
def current_model() -> ModelInfo:
    """サーバーが既定として使うモデルの**解決後**の値を返す。

    UI のヘッダー表示と、モデルセレクタの「（既定値: …）」に実名を出すために
    使う。フロントに既定値を焼き付けると、`config/grace_config.yml` を変えた
    ときに画面と実挙動がずれるので、必ずここから取る。
    """
    llm = get_config().llm
    return ModelInfo(
        model=llm.model,
        light_model=llm.light_model,
        heavy_model=llm.heavy_model,
        # データ準備側の既定はスキーマの既定値を唯一の正本として引く
        # （フロントにも yml にも二重で持たせない）。
        chunking_model=ChunkingRequest.model_fields["model"].default,
        qa_model=QaGenerationRequest.model_fields["model"].default,
        embedding_model=ModelConfig.EMBEDDING_MODEL,
        embedding_dims=ModelConfig.EMBEDDING_DIMS,
    )


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


@router.get("/rulesets", response_model=List[RuleSetInfo])
def list_rulesets() -> List[RuleSetInfo]:
    """UI のルールセットセレクタ用に、組み込みルールセットを返す。

    ルール本文（`RuleItem.description`）は LLM プロンプト用で UI では使わないため
    返さない。件数と対象法令だけを出して、選択の判断に足りる情報にとどめる。
    """
    return [
        RuleSetInfo(
            id=key,
            name=ruleset.name,
            collections=list(ruleset.collections),
            rule_count=len(ruleset.rules),
            always_check_count=len(ruleset.always_check_rules),
            laws=sorted({rule.law for rule in ruleset.rules}),
            critical_keywords=list(ruleset.critical_keywords),
            action_map=dict(ruleset.action_map),
            notify_th=ruleset.notify_th,
            confirm_th=ruleset.confirm_th,
            prompt_addendum=ruleset.prompt_addendum,
        )
        for key, ruleset in RULESETS.items()
    ]


@router.get("/health")
def health() -> Dict[str, object]:
    """稼働確認と実行前提（APIキー設定有無）の可視化。"""
    return {
        "status": "ok",
        "anthropic_api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google_api_key": bool(os.getenv("GOOGLE_API_KEY")),
    }
