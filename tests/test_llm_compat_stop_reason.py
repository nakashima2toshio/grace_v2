"""`stop_reason`（拒否・上限到達）の扱いと、planner プロンプトの整合を守るテスト。

## なぜ必要か

Sonnet 5.5 のプロンプトガイドは、`stop_reason: "max_tokens"` の JSON 応答は
有効に見えても失敗として扱って再試行すること、`refusal` は通常の応答として届くことを
求めている。以前の `grace/llm_compat.py` は `stop_reason` を一切見ておらず、
拒否は「本文が空の成功」、上限到達は「途中で切れた JSON」として下流へ流れていた。

また planner の計画生成プロンプトは、検索クエリについて正反対の 2 指示
（「元の質問文を完全一致でコピー、キーワード化は禁止」と「キーワード列に変換せよ」）
を同時に含んでいた。
"""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from grace import llm_compat
from grace.llm_compat import AnthropicGenaiClient


class _Scripted:
    """messages.create の戻りを順に返し、呼び出し引数を記録する。"""

    def __init__(self, *messages):
        self._messages = list(messages)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(dict(kwargs))
        return self._messages.pop(0)


def _msg(text="{}", stop_reason="end_turn", category=None):
    details = SimpleNamespace(category=category) if category else None
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=None,
        stop_reason=stop_reason,
        stop_details=details,
    )


class _Out(BaseModel):
    x: int


def _client(*messages, model="claude-sonnet-5-5"):
    client = AnthropicGenaiClient(default_model=model)
    spy = _Scripted(*messages)
    client._client = SimpleNamespace(messages=spy)
    return client, spy


def _json_cfg(max_tokens=1024):
    return {"response_schema": _Out, "max_output_tokens": max_tokens}


def test_refusal_raises_instead_of_returning_empty_text():
    client, _ = _client(_msg(text="", stop_reason="refusal", category="reasoning_extraction"))

    with pytest.raises(llm_compat.LLMRefusalError) as exc:
        client.models.generate_content(contents="q", config=_json_cfg())

    assert exc.value.category == "reasoning_extraction"


def test_json_truncated_once_is_retried_with_wider_limit():
    client, spy = _client(
        _msg(text='{"x": 1', stop_reason="max_tokens"),
        _msg(text='{"x": 2}', stop_reason="end_turn"),
    )

    res = client.models.generate_content(contents="q", config=_json_cfg(4096))

    assert res.text == '{"x": 2}'
    assert len(spy.calls) == 2
    assert spy.calls[1]["max_tokens"] == 8192


def test_json_truncated_twice_is_a_failure_even_if_text_looks_valid():
    client, spy = _client(
        _msg(text='{"x": 1}', stop_reason="max_tokens"),
        _msg(text='{"x": 1}', stop_reason="max_tokens"),
    )

    with pytest.raises(llm_compat.LLMTruncatedError):
        client.models.generate_content(contents="q", config=_json_cfg(4096))

    assert len(spy.calls) == 2  # 再試行は 1 回だけ


def test_widened_limit_is_capped_by_the_model_maximum():
    client, spy = _client(
        _msg(stop_reason="max_tokens"), _msg(stop_reason="max_tokens"),
    )

    with pytest.raises(llm_compat.LLMTruncatedError):
        client.models.generate_content(contents="q", config=_json_cfg(100_000))

    assert spy.calls[1]["max_tokens"] == 128_000  # claude-sonnet-5-5 の max_output


def test_free_text_truncation_returns_partial_text():
    """自由文（reasoning の回答など）は途中まででも使えるので例外にしない。"""
    client, spy = _client(_msg(text="回答の途中まで", stop_reason="max_tokens"))

    res = client.models.generate_content(contents="q", config={"max_output_tokens": 4096})

    assert res.text == "回答の途中まで"
    assert len(spy.calls) == 1


def test_normal_end_turn_is_unchanged():
    client, spy = _client(_msg(text='{"x": 3}', stop_reason="end_turn"))

    res = client.models.generate_content(contents="q", config=_json_cfg())

    assert res.text == '{"x": 3}'
    assert len(spy.calls) == 1


def test_planner_prompt_has_no_contradicting_query_instruction():
    from grace.planner import PLAN_GENERATION_PROMPT

    # 残すべき指示
    assert "完全一致でコピー" in PLAN_GENERATION_PROMPT
    # 正反対の指示（services/prompts.py::SEARCH_QUERY_INSTRUCTION）が混ざっていないこと
    assert "キーワードのリストとして作成" not in PLAN_GENERATION_PROMPT
    assert "助詞や助動詞" not in PLAN_GENERATION_PROMPT


def test_planner_prompt_placeholders_are_filled_by_format():
    """f-string をやめたので `{{...}}` ではなく `{...}` で埋め込めること（波括弧が残らない）。"""
    from grace.planner import PLAN_GENERATION_PROMPT

    text = PLAN_GENERATION_PROMPT.format(available_collections="COLS", query="QQQ")

    assert "COLS" in text and "QQQ" in text
    assert "{" not in text and "}" not in text
