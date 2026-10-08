# backend/tests/test_qa_default_model.py
"""Q/A 生成の既定モデルが `config.py::ModelConfig.DEFAULT_MODEL` を指すこと。

2026-09-28 に既定を `claude-sonnet-5-5` へ変えたとき、画面の「② Q/A 作成」
（`QaGenerationRequest` / `QaGenerationParams`）だけが追随し、CLI 側
（`make_qa_register_qdrant.py --model` / `make_qa.py --model` / `QAPipeline` /
`SmartQAGenerator` / `helper_rag_qa` の各生成器 / `qa_service`）は
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

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _default(func, name):
    return inspect.signature(func).parameters[name].default


def test_default_model_is_the_current_default():
    assert ModelConfig.DEFAULT_MODEL == "claude-sonnet-5-5"


@pytest.mark.parametrize("path,attr,param", [
    ("qa_generation.pipeline", "QAPipeline.__init__", "model"),
    ("qa_generation.smart_qa_generator", "SmartQAGenerator.__init__", "model"),
    ("services.qa_service", "generate_qa_pairs", "model"),
    ("helper.helper_rag_qa", "QACountOptimizer.__init__", "llm_model"),
    ("helper.helper_rag_qa", "LLMBasedQAGenerator.__init__", "model"),
    ("helper.helper_rag_qa", "ChainOfThoughtQAGenerator.__init__", "model"),
])
def test_library_defaults_follow_model_config(path, attr, param, monkeypatch):
    import importlib
    import importlib.util
    import types

    # helper_rag_qa は先頭で `import spacy` する。spaCy が無い環境では空のモジュールを
    # 差し込む（test_hybrid_qa_generator.py と同じ方法。spacy.load は呼ばない）。
    if importlib.util.find_spec("spacy") is None:
        monkeypatch.setitem(sys.modules, "spacy", types.ModuleType("spacy"))
        monkeypatch.delitem(sys.modules, path, raising=False)

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
