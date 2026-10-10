from unittest.mock import MagicMock, patch

import pytest

from config import ModelConfig
from services.token_service import (
    TokenManager,
    estimate_tokens_simple,
)


class TestTokenService:

    def test_count_tokens_tiktoken(self):
        # Mock tiktoken
        with patch("services.token_service.tiktoken.get_encoding") as mock_get_encoding:
            mock_enc = MagicMock()
            mock_enc.encode.return_value = [1, 2, 3] # 3 tokens
            mock_get_encoding.return_value = mock_enc

            count = TokenManager.count_tokens("ABC")
            assert count == 3
            mock_get_encoding.assert_called_with("cl100k_base")

    def test_count_tokens_fallback(self):
        # tiktoken が失敗したら estimate_tokens_simple へ落ちる
        with patch("services.token_service.tiktoken.get_encoding", side_effect=Exception("Error")):
            assert TokenManager.count_tokens("ABC") == estimate_tokens_simple("ABC")

    def test_estimate_tokens_simple(self):
        # English
        assert estimate_tokens_simple("ABCD") == 1 # 4 * 0.25 = 1
        # Japanese
        assert estimate_tokens_simple("あいう") == 1 # 3 * 0.5 = 1.5 -> 1

    def test_truncate_text(self):
         with patch("services.token_service.tiktoken.get_encoding") as mock_get_encoding:
            mock_enc = MagicMock()
            mock_enc.encode.return_value = [1, 2, 3, 4, 5]
            mock_enc.decode.side_effect = lambda x: f"decoded_{len(x)}"
            mock_get_encoding.return_value = mock_enc

            truncated = TokenManager.truncate_text("ABCDE", max_tokens=3)
            # Should call decode with first 3 tokens
            mock_enc.decode.assert_called()
            args, _ = mock_enc.decode.call_args
            assert len(args[0]) == 3
            assert truncated == "decoded_3"

    def test_estimate_cost(self):
        # LLM: 本プロジェクトの既定モデルは単価表に載っていること（未登録だと既定単価へ黙って落ちる）
        model = ModelConfig.DEFAULT_MODEL
        pricing = TokenManager.LLM_PRICING[model]
        cost = TokenManager.estimate_cost(1000, 1000, model)
        assert cost == pytest.approx(pricing["input"] + pricing["output"])

        # Embedding
        # 既定の Embedding は単価表に載っていること（未登録だと既定単価へ黙って落ちる）
        emb = ModelConfig.EMBEDDING_MODEL
        cost_emb = TokenManager.estimate_cost(1000, 0, emb, is_embedding=True)
        assert cost_emb == pytest.approx(ModelConfig.EMBEDDING_PRICING[emb])

    def test_get_model_limits(self):
        limits = TokenManager.get_model_limits(ModelConfig.DEFAULT_MODEL)
        assert limits == TokenManager.MODEL_LIMITS[ModelConfig.DEFAULT_MODEL]
