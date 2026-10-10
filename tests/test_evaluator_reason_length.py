"""評価 LLM の `reason` を短くさせる指示が、プロンプトに入っていること。

## 背景

ステップ確信度の評価（haiku）は 1 回 3〜4 秒かかり、1 リクエストに 2 回ある
（実測 2026-09-29: 全体 17 秒のうち約 6.6 秒）。出力の大半は `reason`（200〜300 字の
評価理由）で、スコアそのものは数トークンしかない。

JSON はスコアが先・reason が後に出るので、reason を短くさせても**スコアは変わらず**、
出力トークン（＝待ち時間）だけが減る。この指示が消えると待ち時間が戻る。
"""

import json
from types import SimpleNamespace

import pytest

from grace.confidence import (
    ConfidenceFactors,
    FinalEvaluationResult,
    GroundednessResponse,
    GroundednessVerifier,
    LLMSelfEvaluator,
)
from grace.config import get_config

LIMIT_PHRASE = "80 字以内"


@pytest.fixture(autouse=True)
def _dummy_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")


def test_final_eval_prompt_asks_for_a_short_reason():
    prompt = LLMSelfEvaluator.FINAL_EVAL_PROMPT
    assert LIMIT_PHRASE in prompt
    # .format() で壊れない（波括弧の扱い）
    prompt.format(query="q", answer="a", sources="s")


def test_groundedness_prompt_asks_for_a_short_reason():
    prompt = GroundednessVerifier.PROMPT
    assert LIMIT_PHRASE in prompt
    prompt.format(query="q", answer="a", sources="s")


def test_schema_descriptions_ask_for_a_short_reason():
    """スキーマの説明は JSON Schema のヒントとして LLM に渡る。"""
    assert LIMIT_PHRASE in FinalEvaluationResult.model_fields["reason"].description
    assert LIMIT_PHRASE in GroundednessResponse.model_fields["reason"].description


def test_step_evaluation_prompt_asks_for_a_short_reason():
    """ステップ確信度の評価（haiku）が実際に送るプロンプトを捕まえて確かめる。"""
    seen = {}

    def gen(**kw):
        seen["prompt"] = kw["contents"]
        return SimpleNamespace(text=json.dumps({"score": 0.8, "reason": "十分"}))

    evaluator = LLMSelfEvaluator(config=get_config())
    evaluator.client = SimpleNamespace(models=SimpleNamespace(generate_content=gen))

    evaluator.evaluate_with_factors(
        description="関連情報を検索", output="出力", factors=ConfidenceFactors(), query="q"
    )

    assert LIMIT_PHRASE in seen["prompt"]
    assert '{"score": 0.0, "reason": "評価理由"}' in seen["prompt"]  # JSON 形式の指示は残す
