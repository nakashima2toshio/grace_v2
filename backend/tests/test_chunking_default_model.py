# backend/tests/test_chunking_default_model.py
"""チャンキングの既定モデルが `config.py::ModelConfig.CHUNKING_MODEL` の 1 箇所で決まること。

チャンキングは回答生成・Q/A 生成（`ModelConfig.DEFAULT_MODEL` = Sonnet 5.5）とは**分けて**、
軽量の Haiku 5.5 を使う。以前は `claude-haiku-5-5` が画面・ジョブ・CLI・関数の既定に
6 か所直書きされていた。また、チャンク化専用の `AsyncAPIClient` の既定だけが
`DEFAULT_MODEL` を指しており、モデル名が渡らなかった呼び出しは Sonnet 5.5 へ回避されていた。
"""
from __future__ import annotations

import asyncio
import inspect
import os
import pathlib
import subprocess
import sys

import pytest

from config import ModelConfig

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_chunking_model_is_haiku_5_5_and_separate_from_default():
    assert ModelConfig.CHUNKING_MODEL == "claude-haiku-5-5"
    assert ModelConfig.CHUNKING_MODEL != ModelConfig.DEFAULT_MODEL
    assert ModelConfig.CHUNKING_MODEL in ModelConfig.SELECTABLE_MODELS


def test_web_defaults_follow_chunking_model():
    from backend.app.core.data_jobs import ChunkingParams
    from backend.app.schemas import ChunkingRequest

    assert ChunkingRequest(input_file="OUTPUT/a.csv").model == ModelConfig.CHUNKING_MODEL
    assert ChunkingParams(input_file="OUTPUT/a.csv").model == ModelConfig.CHUNKING_MODEL


def test_library_defaults_follow_chunking_model():
    from chunking.async_api_client import AsyncAPIClient
    from chunking.csv_text_to_chunks_text_csv import chunks_all_async
    from qa_qdrant.make_qa_register_qdrant import CHUNK_DEFAULT_MODEL

    assert inspect.signature(chunks_all_async).parameters["model"].default == ModelConfig.CHUNKING_MODEL
    assert inspect.signature(AsyncAPIClient.__init__).parameters["default_model"].default == ModelConfig.CHUNKING_MODEL
    assert CHUNK_DEFAULT_MODEL == ModelConfig.CHUNKING_MODEL


def test_chunks_all_async_gives_the_client_the_same_model(monkeypatch):
    """クライアントの既定（モデル名が渡らなかったときの回避先）も選んだモデルにする。"""
    import chunking.csv_text_to_chunks_text_csv as mod

    captured = {}

    class _Stop(Exception):
        pass

    def fake_client(**kwargs):
        captured.update(kwargs)
        raise _Stop

    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    monkeypatch.setattr(mod, "AsyncAPIClient", fake_client)
    with pytest.raises(_Stop):
        asyncio.run(mod.chunks_all_async("テキスト", model="claude-opus-5-5"))
    assert captured["default_model"] == "claude-opus-5-5"


def test_chunking_cli_default_follows_chunking_model():
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "chunking.csv_text_to_chunks_text_csv", "--help"],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    flat = "".join(proc.stdout.split())  # argparse の折り返しを無視する
    assert f"デフォルト:{ModelConfig.CHUNKING_MODEL}。" in flat
