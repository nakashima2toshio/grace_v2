"""既定モデルが config.py の価格表・上限表に載っていることを検証する。

## なぜ必要か

`ModelConfig.get_model_pricing()` / `get_model_limits()` はどちらも
`.get(model, <既定>)` で引く。**表に無いモデル名を渡しても落ちず、静かに
汎用の既定値へフォールバックする**ため、行の抜けはテストでしか捕まらない。

実際、チャンキングの既定 `claude-haiku-4-5`（日付サフィックス無し）は
`MODEL_PRICING` / `MODEL_LIMITS` に無く、**コストとトークン上限が実態と違う値で
計算されていた**（2026-09-12 に実機の「データ管理 → ① チャンキング」画面で発見）。

⚠️ モデル名そのものは正しい。`claude-haiku-4-5` と `claude-haiku-4-5-20251001` は
**どちらも実在する**（CLAUDE.md R1）。問題は「表に片方しか載っていない」ことなので、
**モデル名を書き換えて直さないこと**。行を足して直す。
"""

import config
from config import ModelConfig

# 各所の既定モデル。ここを増やしたら config.py の 2 つの表にも行を足す。
DEFAULT_MODELS = {
    # backend/app/core/data_jobs.py::ChunkingParams.model
    # chunking/csv_text_to_chunks_text_csv.py::chunks_all_async / CLI --model
    # frontend/src/components/DataJobPanel.tsx の useState 初期値
    "claude-haiku-4-5": "チャンキングの既定",
    # backend/app/core/data_jobs.py::QaGenerationParams.model
    # qa_qdrant/make_qa.py / make_qa_register_qdrant.py の CLI --model 既定
    # qa_generation/pipeline.py::QAPipeline / smart_qa_generator.py
    "claude-sonnet-5": "Q/A 生成・LLM 全般の既定",
    # config.ModelConfig の軽量モデル（grace/config.py::llm.light_model）
    "claude-haiku-4-5-20251001": "軽量モデル（日付指定）",
    # UI（GET /api/models）で選べる上位モデル
    "claude-opus-5": "上位モデル（モデルセレクタの選択肢）",
    # 旧既定。既存設定ファイルを読み込む環境がまだ指しうる
    "claude-sonnet-4-6": "旧既定（後方互換）",
}


def test_default_models_have_pricing_rows():
    """既定モデルが MODEL_PRICING に載っていること（フォールバックしない）。"""
    missing = [
        f"{name}（{why}）"
        for name, why in DEFAULT_MODELS.items()
        if name not in ModelConfig.MODEL_PRICING
    ]
    assert not missing, (
        "既定モデルが ModelConfig.MODEL_PRICING に無い: "
        + " / ".join(missing)
        + "。.get() の既定値へ静かにフォールバックし、コストが実態と違う値になる。"
        + "モデル名を書き換えるのではなく、表に行を足して直すこと。"
    )


def test_default_models_have_limit_rows():
    """既定モデルが MODEL_LIMITS に載っていること（フォールバックしない）。"""
    missing = [
        f"{name}（{why}）"
        for name, why in DEFAULT_MODELS.items()
        if name not in ModelConfig.MODEL_LIMITS
    ]
    assert not missing, (
        "既定モデルが ModelConfig.MODEL_LIMITS に無い: "
        + " / ".join(missing)
        + "。トークン上限が汎用の既定値（128000/4096）で計算される。"
    )


def test_lookup_does_not_fall_back_for_defaults():
    """引いた値が汎用フォールバックと一致しないこと（= 実際に表から引けている）。"""
    generic_pricing = {"input": 0.00015, "output": 0.0006}
    generic_limits = {"max_tokens": 128000, "max_output": 4096}
    for name in DEFAULT_MODELS:
        pricing = ModelConfig.MODEL_PRICING.get(name, generic_pricing)
        limits = ModelConfig.MODEL_LIMITS.get(name, generic_limits)
        assert pricing is not generic_pricing, f"{name} の単価がフォールバックしている"
        assert limits is not generic_limits, f"{name} の上限がフォールバックしている"
        # フォールバック値（128000）を掴んでいないこと。世代でコンテキスト長が
        # 違う（Sonnet 5 / Opus 5 は 1M、Haiku 4.5 と旧 Sonnet 4.6 は 200k）ので
        # 特定の値では固定せず、「汎用既定ではない」ことだけを見る。
        assert limits["max_tokens"] != generic_limits["max_tokens"], (
            f"{name} の max_tokens が {limits['max_tokens']}（汎用フォールバック値）。"
            "表に行が無い。"
        )


def test_available_models_are_priced():
    """AVAILABLE_MODELS に挙げたモデルはすべて両方の表に載っていること。"""
    for name in ModelConfig.AVAILABLE_MODELS:
        assert name in ModelConfig.MODEL_PRICING, f"{name} が MODEL_PRICING に無い"
        assert name in ModelConfig.MODEL_LIMITS, f"{name} が MODEL_LIMITS に無い"


def test_config_module_is_the_repo_one():
    """取り違え防止: 参照している config が本リポジトリのものであること。"""
    assert hasattr(config, "ModelConfig")
    assert ModelConfig.DEFAULT_MODEL == "claude-sonnet-5"
