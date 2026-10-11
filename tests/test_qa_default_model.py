# tests/test_qa_default_model.py
"""Q/A 生成の既定モデルが `config.py::ModelConfig.DEFAULT_MODEL` を指すこと。

2026-09-28 に既定を `claude-sonnet-5-5` へ変えたとき、画面の「② Q/A 作成」
（`QaGenerationRequest` / `QaGenerationParams`）だけが追随し、CLI 側
（`make_qa_register_qdrant.py --model` / `make_qa.py --model` / `QAPipeline` /
`SmartQAGenerator` / `qa_service`。当時は `helper/helper_rag_qa.py` の各生成器も。2026-10-11 に削除）は
旧既定 `claude-sonnet-5` を直書きしたまま残っていた。同じ Q/A 生成が、画面からだと
Sonnet 5.5、CLI からだと Sonnet 5 で走っていた。直書きをやめ、正本を参照させる。
"""
from __future__ import annotations

import inspect
import os
import pathlib
import subprocess
import sys

import pytest

from config import ModelConfig

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _default(func, name):
    return inspect.signature(func).parameters[name].default


def test_default_model_is_the_current_default():
    assert ModelConfig.DEFAULT_MODEL == "claude-sonnet-5-5"


@pytest.mark.parametrize("path,attr,param", [
    ("qa_generation.pipeline", "QAPipeline.__init__", "model"),
    ("qa_generation.smart_qa_generator", "SmartQAGenerator.__init__", "model"),
    ("services.qa_service", "generate_qa_pairs", "model"),
])
def test_library_defaults_follow_model_config(path, attr, param):
    import importlib

    obj = importlib.import_module(path)
    for part in attr.split("."):
        obj = getattr(obj, part)
    assert _default(obj, param) == ModelConfig.DEFAULT_MODEL


@pytest.mark.parametrize("script", [
    "qa_qdrant/make_qa_register_qdrant.py",
    "qa_qdrant/make_qa.py",
])
def test_cli_model_default_follows_model_config(script):
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, script, "--help"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    # argparse は長いヘルプを折り返すので、空白を除いて比べる
    flat = "".join(proc.stdout.split())
    assert f"デフォルト:{ModelConfig.DEFAULT_MODEL}）" in flat
