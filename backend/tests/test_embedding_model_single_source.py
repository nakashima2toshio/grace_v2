"""Embedding モデル名の定義が `config.py::ModelConfig` の 1 箇所だけであることを固定するテスト。

2026-09-26 まで、Embedding のモデル名（当時 `gemini-embedding-001`）は
コード 12 ファイル・設定ファイル 2 つ・画面に直書きされていた。実際に API を呼ぶ
`GeminiEmbedding` の既定引数、`grace/config.py::EmbeddingConfig`（と、それを上書きする
`config/grace_config.yml`）、`QdrantConfig`、単価表 3 つ（`helper_embedding` /
`helper_llm` / `token_service`）が、それぞれ別々にモデル名を持っていた。
そのため 1 箇所だけ変えると、登録と検索で違うモデルが使われうる。
次元が同じなのでエラーにならず、検索結果だけが静かに壊れる。

モデル名は `ModelConfig.EMBEDDING_MODEL`（Anthropic の LLM と同じクラス）に 1 つだけ書き、
他はそれを参照する形にした。ここでは、その形が崩れていないこと（リテラルが増えていないこと・
各参照先が同じ値を指していること）を検査する。API キーは不要。
"""

import inspect
import re
from pathlib import Path

import yaml

import helper.helper_llm as helper_llm
import services.token_service as token_service
from chunking.csv_text_to_chunks_text_csv import (
    EMBEDDING_INPUT_TOKEN_LIMIT,
    MAX_CHUNK_TOKENS,
)
from config import GeminiConfig, ModelConfig, QdrantConfig
from grace.config import EmbeddingConfig, get_config
from helper.helper_embedding import EMBEDDING_PRICING, GeminiEmbedding
from qdrant_client_wrapper import COLLECTION_EMBEDDINGS_GEMINI, PROVIDER_DEFAULTS

ROOT = Path(__file__).resolve().parents[2]

# 文字列リテラルとして書かれた Gemini Embedding のモデル名（コメント中の言及は対象外）
_LITERAL = re.compile(r"""["']gemini-embedding-[\w.-]+["']""")
_SKIP_DIRS = {".venv", "node_modules", "__pycache__", ".git", "old_code", "tests"}


def _code_files():
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if _SKIP_DIRS.intersection(rel.parts):
            continue
        yield rel, path.read_text(encoding="utf-8", errors="ignore")


def test_model_name_literal_only_in_config_py():
    """Embedding のモデル名を文字列で書いてよいのは config.py だけ。"""
    offenders = {
        str(rel): _LITERAL.findall(text)
        for rel, text in _code_files()
        if rel != Path("config.py") and _LITERAL.search(text)
    }
    assert offenders == {}, f"config.py 以外に Embedding モデル名のリテラルがある: {offenders}"


def test_grace_config_yml_does_not_redefine_embedding_model():
    """grace_config.yml に model / dimensions を書くと、ModelConfig の既定を素通りする。"""
    data = yaml.safe_load((ROOT / "config" / "grace_config.yml").read_text(encoding="utf-8"))
    embedding = data.get("embedding") or {}
    assert "model" not in embedding
    assert "dimensions" not in embedding


def test_all_consumers_resolve_to_model_config():
    """実際に使われる経路がすべて ModelConfig の値に解決されること。"""
    model = ModelConfig.EMBEDDING_MODEL
    dims = ModelConfig.EMBEDDING_DIMS

    # 実際に embed_content を呼ぶクライアントの既定引数
    params = inspect.signature(GeminiEmbedding.__init__).parameters
    assert params["model"].default == model
    assert params["dims"].default == dims

    # GRACE 本体（grace_config.yml → GraceConfig の解決後）
    assert EmbeddingConfig().model == model
    assert get_config().embedding.model == model
    assert get_config().embedding.dimensions == dims

    # 旧来の参照口
    assert GeminiConfig.EMBEDDING_MODEL == model
    assert GeminiConfig.EMBEDDING_DIMS == dims
    assert QdrantConfig.DEFAULT_EMBEDDING_MODEL == model
    assert QdrantConfig.DEFAULT_VECTOR_SIZE == dims
    assert PROVIDER_DEFAULTS["gemini"]["model"] == model
    assert all(spec["model"] == model for spec in COLLECTION_EMBEDDINGS_GEMINI.values())


def test_pricing_tables_share_one_definition():
    """単価表は ModelConfig.EMBEDDING_PRICING を指し、既定モデルの単価が載っていること。"""
    for table in (EMBEDDING_PRICING, helper_llm.EMBEDDING_PRICING, token_service.EMBEDDING_PRICING):
        assert table is ModelConfig.EMBEDDING_PRICING
    assert ModelConfig.EMBEDDING_MODEL in ModelConfig.EMBEDDING_PRICING
    assert helper_llm.EMBEDDING_DIMS[ModelConfig.EMBEDDING_MODEL] == ModelConfig.EMBEDDING_DIMS


def test_chunk_size_stays_below_embedding_input_limit():
    """チャンクの上限は Embedding の入力上限未満（超えると超過分が無言で切り捨てられる）。"""
    assert EMBEDDING_INPUT_TOKEN_LIMIT == ModelConfig.EMBEDDING_MAX_INPUT_TOKENS
    assert MAX_CHUNK_TOKENS < EMBEDDING_INPUT_TOKEN_LIMIT
