"""軽量モデルの既定が Claude Haiku 5.5（`claude-haiku-5-5`）であることを固定するテスト。

2026-10-08 に軽量モデルを Haiku 4.5 から Haiku 5.5 へ切り替えた。
CLAUDE.md §3.1 のとおり、モデル名の解決経路は複数あり、1 か所だけ直すと取り残しが出る。
ここでは「軽量モデル・チャンキングの既定が揃って Haiku 5.5 を指しているか」と
「Haiku 5.5 がモデル表すべてに載っているか」を見る。

⚠️ Haiku 4.5（`claude-haiku-4-5` / `claude-haiku-4-5-20251001`）は**今も有効なモデル名**で、
既存設定の読み込み用に表へ残す（CLAUDE.md R1・モデル名のマッピングを作らない）。
"""

import pytest

HAIKU_55 = "claude-haiku-5-5"


def test_light_model_defaults_to_haiku_5_5():
    """判定系の軽量モデル（経路 1: grace_config.yml / grace/config.py の既定）。"""
    from grace.config import GraceConfig, get_config

    assert get_config().llm.light_model == HAIKU_55
    assert GraceConfig().llm.light_model == HAIKU_55


def test_intent_model_fallback_is_haiku_5_5():
    """経路 2（verticals.INTENT_MODEL）も揃える。経路 1 と食い違うとテストで表面化しない。"""
    from backend.app.core.verticals import INTENT_MODEL

    assert INTENT_MODEL == HAIKU_55


def test_chunking_defaults_to_haiku_5_5():
    """チャンキングの既定（API・ジョブ・CLI・一括スクリプト）が揃っていること。"""
    import inspect

    from backend.app.core.data_jobs import ChunkingParams
    from backend.app.schemas import ChunkingRequest
    from chunking.csv_text_to_chunks_text_csv import chunks_all_async
    from qa_qdrant.make_qa_register_qdrant import CHUNK_DEFAULT_MODEL

    assert ChunkingRequest(input_file="a/b.csv").model == HAIKU_55
    assert ChunkingParams(input_file="a/b.csv").model == HAIKU_55
    assert inspect.signature(chunks_all_async).parameters["model"].default == HAIKU_55
    assert CHUNK_DEFAULT_MODEL == HAIKU_55


def test_haiku_5_5_is_the_selectable_light_model():
    """UI の選択肢の軽量枠は Haiku 5.5（4.5 は選択肢から外し、設定からは指定できる）。"""
    from config import ModelConfig

    assert HAIKU_55 in ModelConfig.SELECTABLE_MODELS
    assert "claude-haiku-4-5" not in ModelConfig.SELECTABLE_MODELS
    assert "claude-haiku-4-5" in ModelConfig.AVAILABLE_MODELS
    assert "claude-haiku-4-5-20251001" in ModelConfig.AVAILABLE_MODELS


def test_haiku_5_5_request_rules():
    """Haiku 5.5 は temperature が 400、budget_tokens も 400（adaptive のみ）。
    thinking の disabled は受け付ける（effort high 以下）ので ALWAYS ではない。"""
    from config import ModelConfig

    assert not ModelConfig.supports_temperature(HAIKU_55)
    assert ModelConfig.uses_adaptive_thinking(HAIKU_55)
    assert not ModelConfig.thinking_always_on(HAIKU_55)


@pytest.mark.parametrize(
    "table_path",
    [
        "config.ModelConfig.MODEL_PRICING",
        "config.ModelConfig.MODEL_LIMITS",
        "helper.helper_llm.LLM_PRICING",
        "helper.helper_llm.LLM_LIMITS",
        "services.token_service.LLM_PRICING",
        "services.token_service.MODEL_LIMITS",
    ],
)
def test_haiku_5_5_has_rows_in_every_model_table(table_path):
    """表に無いと `.get()` が汎用の既定値へ黙って落ちる（test_model_table_coverage と同じ理由）。"""
    import importlib

    module_name, *attrs = table_path.split(".")
    obj = importlib.import_module(module_name)
    for attr in attrs:
        obj = getattr(obj, attr)
    assert HAIKU_55 in obj, f"{table_path} に {HAIKU_55} の行が無い"


def test_haiku_5_5_pricing_and_limits_values():
    """$0.10 / $0.50 per MTok（プロンプト 100K トークン以下の料金）・1M コンテキスト・128K 出力。"""
    from config import ModelConfig

    assert ModelConfig.MODEL_PRICING[HAIKU_55] == {"input": 0.0001, "output": 0.0005}
    assert ModelConfig.MODEL_LIMITS[HAIKU_55] == {"max_tokens": 1000000, "max_output": 128000}
