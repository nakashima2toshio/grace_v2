"""既定モデル名の実体が `config.py::ModelConfig` の 1 か所だけであること。

2026-10-14 まで、既定モデル名は次の場所に同じ文字列で書かれていた
（CLAUDE.md §3.1 の「解決経路」）。

- `config/grace_config.yml` の `llm.model` / `llm.light_model`（yml はクラス既定より優先される）
- `grace/config.py::LLMConfig` のクラス既定
- `backend/app/core/verticals.py::INTENT_MODEL`
- `backend/app/core/data_jobs.py::QaGenerationParams.model` / `backend/app/schemas.py::QaGenerationRequest.model`
- `grace/llm_compat.py::DEFAULT_ANTHROPIC_MODEL` / `helper/helper_llm.py::AnthropicClient` の既定引数

1 か所だけ直すと、画面・判定系・CLI でモデルが割れる。grace_v2_local と同じく
既定は `ModelConfig.DEFAULT_MODEL`（推論・生成）と `ModelConfig.LIGHT_MODEL`（判定系）の
2 つの定数だけに置き、ほかはそれを参照する。
"""

from __future__ import annotations

import inspect
from pathlib import Path

import yaml

from config import ModelConfig

ROOT = Path(__file__).resolve().parents[1]

# 既定モデル名を直書きしてはいけないファイル（モデル表・単価表を持つファイルは対象外）
_NO_LITERAL_FILES = [
    "grace/config.py",
    "grace/llm_compat.py",
    "backend/app/core/verticals.py",
    "backend/app/core/data_jobs.py",
    "backend/app/schemas.py",
]


def test_yaml_does_not_pin_model_names():
    """yml の値はクラス既定より優先されるので、置くと config.py を素通りする。"""
    raw = yaml.safe_load((ROOT / "config" / "grace_config.yml").read_text(encoding="utf-8"))
    llm = raw.get("llm") or {}
    assert "model" not in llm
    assert "light_model" not in llm


def test_light_model_constant_exists():
    assert ModelConfig.LIGHT_MODEL in ModelConfig.SELECTABLE_MODELS
    assert ModelConfig.DEFAULT_MODEL in ModelConfig.SELECTABLE_MODELS


def test_loaded_config_follows_model_config(monkeypatch):
    """config.py 側の既定を変えると、yml を読んだ設定もそのモデルになる。"""
    from grace.config import ConfigLoader

    monkeypatch.setattr(ModelConfig, "DEFAULT_MODEL", "one-source-check-main")
    monkeypatch.setattr(ModelConfig, "LIGHT_MODEL", "one-source-check-light")
    cfg = ConfigLoader(str(ROOT / "config" / "grace_config.yml")).load()

    assert cfg.llm.model == "one-source-check-main"
    assert cfg.llm.light_model == "one-source-check-light"


def test_grace_env_override_still_wins(monkeypatch):
    """1 回だけ別モデルで動かす GRACE_LLM_MODEL は引き続き効く。"""
    from grace.config import ConfigLoader

    monkeypatch.setenv("GRACE_LLM_MODEL", "claude-opus-5-5")
    cfg = ConfigLoader(str(ROOT / "config" / "grace_config.yml")).load()

    assert cfg.llm.model == "claude-opus-5-5"


def test_other_defaults_follow_model_config():
    from backend.app.core.data_jobs import QaGenerationParams
    from backend.app.core.verticals import INTENT_MODEL
    from backend.app.schemas import QaGenerationRequest
    from grace.llm_compat import DEFAULT_ANTHROPIC_MODEL
    from helper.helper_llm import AnthropicClient

    assert INTENT_MODEL == ModelConfig.LIGHT_MODEL
    assert DEFAULT_ANTHROPIC_MODEL == ModelConfig.DEFAULT_MODEL
    assert QaGenerationParams.__dataclass_fields__["model"].default == ModelConfig.DEFAULT_MODEL
    assert QaGenerationRequest.model_fields["model"].default == ModelConfig.DEFAULT_MODEL
    assert AnthropicClient(api_key="dummy").default_model == ModelConfig.DEFAULT_MODEL
    assert inspect.signature(AnthropicClient).parameters["default_model"].default is None


def test_no_model_literal_outside_config_py():
    """既定モデル名の文字列を config.py 以外に直書きしない。"""
    names = {ModelConfig.DEFAULT_MODEL, ModelConfig.LIGHT_MODEL}
    offenders = []
    for rel in _NO_LITERAL_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for name in names:
            if f'"{name}"' in text:
                offenders.append(f"{rel}: {name}")
    assert offenders == []
