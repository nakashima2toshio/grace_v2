"""LLM プロバイダ名の検証を固定するテスト。

2026-09-26 まで、未知のプロバイダ名は黙って別のプロバイダへ倒れていた
（姉妹リポジトリ grace_v2_local と同じ問題・同じ修正）。

- `helper.helper_llm.create_llm_client()`: 最後の分岐で **GeminiClient**。`"anthropc"` の
  打ち間違いでも、本リポジトリでは Embedding に必須の `GOOGLE_API_KEY` がある環境なら
  **エラーにならずに Gemini LLM API を呼んでいた**。環境変数 `LLM_PROVIDER` の打ち間違いも同じ。
- `grace.llm_compat.create_chat_client()`: 既定の Anthropic。`grace_config.yml` の
  `llm.provider` の打ち間違いに気付けない（設定の読み込み時にも検証されない）。

どちらも未知の名前は ValueError にした。LLM クライアントは遅延生成なので、実 API は呼ばない。
"""

from unittest.mock import MagicMock, patch

import pytest

import helper.helper_llm as hl
from grace.config import GraceConfig, LLMConfig
from grace.llm_compat import AnthropicGenaiClient, create_chat_client
from helper.helper_llm import AnthropicClient, GeminiClient, create_llm_client

# =============================================================================
# helper.helper_llm.create_llm_client
# =============================================================================


@pytest.mark.parametrize("provider", ["anthropc", "claude-sonnet", "olama"])
def test_create_llm_client_rejects_unknown_provider(monkeypatch, provider):
    """未知の名前は、Embedding 用の GOOGLE_API_KEY があっても Gemini にせず ValueError。"""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    with patch("google.genai.Client") as genai_client:
        with pytest.raises(ValueError, match=provider):
            create_llm_client(provider)
        genai_client.assert_not_called()


def test_create_llm_client_rejects_unknown_default_from_env(monkeypatch):
    """環境変数 LLM_PROVIDER の打ち間違いも、引数なしの呼び出しで止まる。"""
    monkeypatch.setattr(hl, "DEFAULT_LLM_PROVIDER", "anthropc")
    with pytest.raises(ValueError, match="anthropc"):
        create_llm_client()


def test_create_llm_client_anthropic_is_unchanged(monkeypatch):
    """既定の anthropic は従来どおり AnthropicClient。"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    assert isinstance(create_llm_client("anthropic"), AnthropicClient)


@pytest.mark.parametrize("provider", ["gemini", "google", "Gemini"])
def test_create_llm_client_gemini_is_explicit(monkeypatch, provider):
    """gemini / google を明示したときだけ GeminiClient（後方互換）。"""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    with patch("google.genai.Client"):
        assert isinstance(create_llm_client(provider), GeminiClient)


# =============================================================================
# grace.llm_compat.create_chat_client
# =============================================================================


def _config(provider: str) -> GraceConfig:
    return GraceConfig(llm=LLMConfig(provider=provider))


@pytest.mark.parametrize("provider", ["anthropc", "olama", "openai"])
def test_create_chat_client_rejects_unknown_provider(provider):
    """未知の config.llm.provider は、黙って Anthropic へ倒さずに ValueError。"""
    with pytest.raises(ValueError, match=provider):
        create_chat_client(_config(provider))


@pytest.mark.parametrize("provider", ["anthropic", "Anthropic", "claude"])
def test_create_chat_client_anthropic_is_unchanged(provider):
    """anthropic（と別名 claude）は従来どおり AnthropicGenaiClient。"""
    assert isinstance(create_chat_client(_config(provider)), AnthropicGenaiClient)


def test_create_chat_client_defaults_are_unchanged():
    """config なし・文字列でない provider（テストの MagicMock 等）は従来どおり既定の Anthropic。"""
    assert isinstance(create_chat_client(None), AnthropicGenaiClient)
    assert isinstance(create_chat_client(MagicMock()), AnthropicGenaiClient)
