# backend/app/core/verticals.py
"""業界プロファイル（VerticalProfile）定義。

`agent_support_example.py` から移設（React マイグレーション）。CLI・API の
双方から参照される。後方互換のため `agent_support_example` が再エクスポートする。
設計: grace/doc/agent_support_verticals.md §1/§6。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

DEFAULT_QUERY = "パスワードを忘れました"

Decision = Literal["answer", "escalate"]
ActionType = Literal["create_ticket", "send_reply", "escalate_to_human"]

# 意図分類（二段判定の第 2 段）:
#   question = 情報・手順・規定を知りたい（FAQ質問） / request = 操作・手続きの実行依頼
#   incident = 障害・被害・トラブルの発生報告
Intent = Literal["question", "request", "incident"]

# 意図分類に使う軽量モデル（CLAUDE.md プロバイダ方針の軽量既定）
INTENT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class ActionRequest:
    """副作用のある操作の要求（v3・擬似）。"""

    action_type: ActionType
    args: dict = field(default_factory=dict)
    requires_confirmation: bool = True


@dataclass
class VerticalProfile:
    """業界プロファイル（差し替えの共通枠）。設計: agent_support_verticals.md §1/§6。"""

    name: str
    collections: List[str] = field(default_factory=list)   # 検索スコープ（実 Qdrant コレクション名）
    escalate_keywords: List[str] = field(default_factory=list)  # 強制エスカレ語
    action_map: Dict[str, ActionType] = field(default_factory=dict)  # 意図キーワード → action_type
    require_identity: bool = False           # アクション前に本人確認を必須化
    notify_th: Optional[float] = None        # None なら config 既定
    confirm_th: Optional[float] = None
    prompt_addendum: str = ""                # 業界固有の方針（表示・将来のプロンプト注入用）


# 組み込みプロファイル（自治体 / SaaS / EC）
#
# collections は実 Qdrant コレクション名（命名規約 `*_anthropic`。
# docs/vertical_test_data.md 参照）。RAG 検索は config.qdrant.allowed_collections
# 経由でこのスコープに限定される。未登録のコレクションは自動的に無視され、
# 1 つも登録が無い場合は制限なし（既定コレクション横断）で従来どおり動作する。
PROFILES: Dict[str, VerticalProfile] = {
    "gov": VerticalProfile(
        name="自治体",
        # wikipedia_ja は専用コレクション（gov_faq/gov_laws）登録までの代替
        collections=["gov_faq_anthropic", "gov_laws_anthropic", "wikipedia_ja"],
        escalate_keywords=["法的", "訴訟", "減免", "個別", "例外", "不服"],
        action_map={"申請": "send_reply", "手続": "send_reply", "様式": "send_reply"},
        require_identity=False,
        notify_th=0.8, confirm_th=0.5,   # 正確性最優先：厳しめ
        prompt_addendum="条例・公式案内に基づき、断定を避け、該当ページ・担当課を明示。個人情報は尋ねない。",
    ),
    "saas": VerticalProfile(
        name="SaaS",
        collections=["saas_docs_anthropic", "saas_api_anthropic"],
        escalate_keywords=["障害", "ダウン", "落ち", "課金", "請求", "情報漏", "セキュリティ"],
        action_map={"エラー": "create_ticket", "不具合": "create_ticket", "バグ": "create_ticket"},
        require_identity=False,
        prompt_addendum="製品バージョンを明示し、再現手順と公式ドキュメント URL を添える。",
    ),
    "ec": VerticalProfile(
        name="EC",
        collections=["ec_policy_anthropic", "ec_faq_anthropic"],
        escalate_keywords=["決済", "返金", "破損", "クレーム", "不良品"],
        action_map={"返品": "create_ticket", "交換": "create_ticket",
                    "キャンセル": "create_ticket", "解約": "create_ticket"},
        require_identity=True,           # 注文情報の操作は本人確認必須
        prompt_addendum="注文情報の照会・変更は本人確認必須。返品・交換は規定の版に基づいて回答。",
    ),
}
