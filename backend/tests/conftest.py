# backend/tests/conftest.py
"""backend テスト共通フィクスチャ。

`run_support_agent_core` の外部依存（planner/executor/verifier/tools/LLM 分類器）を
スタブへ差し替え、API キー・Qdrant・実 LLM なしでパイプラインの配線
（イベント・HITL・判定の流れ）を検証できるようにする。判定に使う純関数
（`_answer_gate` / `_decide_action` 等）は backend/app/core/gates.py 側にあり、
本ディレクトリの test_support_agent_core.py が配線ごと固定している。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import List, Optional

import pytest


def make_config_stub(notify=0.7, confirm=0.4, default_timeout=2):
    """get_config() 互換の最小スタブ（core が触る属性のみ）。"""
    return SimpleNamespace(
        confidence=SimpleNamespace(
            thresholds=SimpleNamespace(silent=0.9, notify=notify, confirm=confirm)
        ),
        qdrant=SimpleNamespace(allowed_collections=[]),
        llm=SimpleNamespace(prompt_addendum=""),
        # W-1: 業界プロファイル由来の優先ドメインの注入先
        web_search=SimpleNamespace(preferred_domains=[], preferred_domain_boost=0.15),
        intervention=SimpleNamespace(
            default_timeout=default_timeout, auto_proceed_on_timeout=False
        ),
    )


@dataclass
class GroundednessStub:
    support_rate: float = 0.9
    supported: int = 3
    contradicted: int = 0
    total: int = 3
    verified: bool = True
    has_contradiction: bool = False


@dataclass
class StepResultStub:
    step_id: int = 1
    status: str = "success"
    sources: List[str] = field(default_factory=lambda: ["faq.md"])
    # 根拠検証用の出典本文（実 executor の StepResult.source_texts に対応）。
    # 既定は空 = 本文が取れない経路を模し、出典ラベルへのフォールバックを検証する。
    source_texts: List[str] = field(default_factory=list)


@dataclass
class PipelineStub:
    """1 シナリオ分のパイプライン外部依存の応答定義。"""

    answer: str = "パスワード再設定はマイページの「パスワードを忘れた方」から行えます。"
    sources: List[str] = field(default_factory=lambda: ["faq.md"])
    # 出典本文（groundedness 検証に渡る想定のテキスト）。空なら出典ラベルへ
    # フォールバックする従来経路を再現する。
    source_texts: List[str] = field(default_factory=list)
    # 検証器へ実際に渡されたソースを記録する（P-01 の回帰検証用）
    verify_calls: List[list] = field(default_factory=list)
    groundedness: GroundednessStub = field(default_factory=GroundednessStub)
    intent: Optional[str] = None            # 意図分類器の返答（None=分類失敗）
    no_info_verdict: Optional[bool] = False  # 実質回答判定（False=answered）
    web_output: Optional[list] = None        # ⑤ の web_search 結果
    overall_confidence: float = 0.85
    config: SimpleNamespace = field(default_factory=make_config_stub)


def install_pipeline_stub(monkeypatch, stub: PipelineStub) -> None:
    """backend.app.core.support_agent の外部依存をスタブへ差し替える。"""
    target = "backend.app.core.support_agent"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(f"{target}.get_config", lambda: stub.config)

    plan = SimpleNamespace(steps=[SimpleNamespace(step_id=1)], complexity=0.2)
    planner = SimpleNamespace(create_plan=lambda _q: plan)
    monkeypatch.setattr(f"{target}.create_planner", lambda _c: planner)

    # 実行時に stub を読む（テスト側が設置後に属性を書き換えられるよう遅延評価）
    executor = SimpleNamespace(execute=lambda _plan: SimpleNamespace(
        final_answer=stub.answer,
        step_results=[StepResultStub(
            sources=list(stub.sources),
            source_texts=list(stub.source_texts),
        )],
        overall_confidence=stub.overall_confidence,
    ))
    monkeypatch.setattr(f"{target}.create_executor", lambda _c, _r: executor)

    def _verify(_q, _a, sources):
        stub.verify_calls.append(list(sources or []))
        return stub.groundedness

    verifier = SimpleNamespace(verify=_verify)
    monkeypatch.setattr(f"{target}.create_groundedness_verifier", lambda _c: verifier)

    calc = SimpleNamespace(calculate=lambda _answers: 0.9)
    monkeypatch.setattr(
        f"{target}.create_source_agreement_calculator", lambda _c: calc
    )

    def tool_execute(name, **kwargs):
        if name == "web_search":
            return SimpleNamespace(success=True, output=stub.web_output)
        if name == "reasoning":
            return SimpleNamespace(success=True, output="Web 由来の回答")
        raise AssertionError(f"想定外のツール呼び出し: {name}")

    registry = SimpleNamespace(execute=tool_execute)
    monkeypatch.setattr(f"{target}.create_tool_registry", lambda _c: registry)

    def classify(_q: str) -> Optional[str]:
        return stub.intent

    monkeypatch.setattr(f"{target}.create_intent_classifier", lambda _c: classify)

    def judge(_q: str, _a: str) -> Optional[bool]:
        return stub.no_info_verdict

    monkeypatch.setattr(f"{target}.create_no_info_judge", lambda _c: judge)


@pytest.fixture
def pipeline_stub(monkeypatch):
    """既定シナリオ（高支持率・社内出典あり）のスタブを設置して返す。

    テスト側で stub の属性を書き換えてから core を呼べば、シナリオを変えられる
    （設置時に参照を渡しているため）。
    """
    stub = PipelineStub()
    install_pipeline_stub(monkeypatch, stub)
    return stub
