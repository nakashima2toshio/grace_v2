import os
from unittest.mock import mock_open, patch

import pytest

from config import ModelConfig
from services.config_service import ConfigManager


# Reset singleton before each test
@pytest.fixture(autouse=True)
def reset_singleton():
    ConfigManager._instance = None
    yield
    ConfigManager._instance = None

class TestConfigManager:

    def test_singleton(self):
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    def test_load_default(self):
        with patch("services.config_service.Path.exists", return_value=False):
            cm = ConfigManager()
            # Should have defaults
            assert cm.get("api.timeout") == 30
            # `_get_default_config()` はモデル名をリテラルで持つ。`ModelConfig` と食い違うと
            # 直下 `config.yml` が無い環境（CLAUDE.md §3.1 の経路 5 のフォールバック）だけ
            # 別のモデルになるので、正本の `ModelConfig` と突き合わせる。
            assert cm.get("models.default") == ModelConfig.DEFAULT_MODEL
            assert cm.get("models.available") == ModelConfig.SELECTABLE_MODELS

    def test_default_llm_provider_is_anthropic(self):
        """既定の `llm.provider` は本リポジトリの LLM（Anthropic）であること。"""
        env = {k: v for k, v in os.environ.items() if k != "LLM_PROVIDER"}
        with patch("services.config_service.Path.exists", return_value=False), \
             patch.dict(os.environ, env, clear=True):
            cm = ConfigManager()
            assert cm.get("llm.provider") == "anthropic"

    def test_load_yaml(self):
        yaml_content = """
api:
  timeout: 60
models:
  default: "gpt-4"
"""
        with patch("builtins.open", mock_open(read_data=yaml_content)), \
             patch("services.config_service.Path.exists", return_value=True):

            cm = ConfigManager()
            assert cm.get("api.timeout") == 60
            assert cm.get("models.default") == "gpt-4"

    def test_env_override(self):
        with patch("services.config_service.Path.exists", return_value=False), \
             patch.dict(os.environ, {"GOOGLE_API_KEY": "env_key"}):

            cm = ConfigManager()
            assert cm.get("api.google_api_key") == "env_key"

    def test_get_set(self):
        with patch("services.config_service.Path.exists", return_value=False):
            cm = ConfigManager()

            cm.set("new.key", "value")
            assert cm.get("new.key") == "value"

            # Cache check
            cm.set("new.key", "updated")
            assert cm.get("new.key") == "updated"

    def test_get_nested_missing(self):
         with patch("services.config_service.Path.exists", return_value=False):
            cm = ConfigManager()
            assert cm.get("non.existent.key", "default_val") == "default_val"
