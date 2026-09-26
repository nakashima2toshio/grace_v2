# backend/tests/test_model_selection.py
"""ヘッダーのモデルセレクタの回帰テスト。

## 何を守るか

既定は `claude-sonnet-5`、選択肢は `claude-fable-5-1` / `claude-opus-5-5` /
`claude-sonnet-5` / `claude-haiku-4-5` の 4 つ（上位 → 軽量の順）。選択肢の解決は `config.py::get_selectable_models()`
の**1 箇所**に寄せてあり、API のバリデータ・`GET /api/models`・エージェント
コアの上書きがすべてそこを読む。どれか 1 つが独自の一覧を持つと、画面で選べる
のに 422 になる（またはその逆）といった食い違いが起きる。

## ⚠️ Embedding は対象外

Embedding は Gemini（`config.py::ModelConfig.EMBEDDING_MODEL`）固定。モデルを変えると
既存 Qdrant コレクションが使えず全件再登録になるため、**選択肢にも
上書き経路にも出てこない**こと自体をテストで固定する。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.core.verticals import INTENT_MODEL
from backend.app.main import app
from backend.app.schemas import (
    ChunkingRequest,
    QaGenerationRequest,
    QueryRequest,
    ReviewRequest,
)
from backend.tests.conftest import PipelineStub, install_pipeline_stub, make_config_stub
from config import ModelConfig, get_selectable_models

client = TestClient(app)

EXPECTED_CHOICES = [
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-sonnet-5",
    "claude-haiku-4-5",
]


# ---------------------------------------------------------------------------
# 選択肢そのもの
# ---------------------------------------------------------------------------


def test_selectable_models_are_the_four_current_ones():
    """選択肢は現行世代の 4 つだけ（並びはプルダウンの表示順）。"""
    assert get_selectable_models() == EXPECTED_CHOICES


def test_default_model_is_sonnet_5_and_selectable():
    """既定は `claude-sonnet-5`。既定が選択肢に無いと、画面で既定を選び直せない。"""
    assert ModelConfig.DEFAULT_MODEL == "claude-sonnet-5"
    assert ModelConfig.DEFAULT_MODEL in get_selectable_models()


def test_opus_5_is_no_longer_selectable_but_still_known():
    """旧上位 `claude-opus-5` は選択肢から外したが、既存設定（heavy_model 等）の
    ために単価・上限表と AVAILABLE_MODELS には残す（CLAUDE.md R1: 消さない）。"""
    assert "claude-opus-5" not in get_selectable_models()
    assert "claude-opus-5" in ModelConfig.AVAILABLE_MODELS
    assert "claude-opus-5" in ModelConfig.MODEL_PRICING


def test_selectable_models_exclude_legacy_and_dated_alias():
    """旧既定と日付指定エイリアスは**選択肢に出さない**（同じモデルが 2 行出る）。

    どちらも実在する有効なモデル名なので `AVAILABLE_MODELS` からは消さない
    （CLAUDE.md R1）。出さないのは UI の選択肢だけ。
    """
    choices = get_selectable_models()

    assert "claude-sonnet-4-6" not in choices
    assert "claude-haiku-4-5-20251001" not in choices
    # ただし単価・上限を引く側には残っている
    assert "claude-sonnet-4-6" in ModelConfig.AVAILABLE_MODELS
    assert "claude-haiku-4-5-20251001" in ModelConfig.AVAILABLE_MODELS


def test_selectable_models_are_subset_of_available():
    """選択肢はすべて単価表・上限表を持つ（コストが汎用既定へ落ちない）。"""
    for name in get_selectable_models():
        assert name in ModelConfig.AVAILABLE_MODELS
        assert name in ModelConfig.MODEL_PRICING
        assert name in ModelConfig.MODEL_LIMITS


def test_selectable_models_contain_no_embedding_model():
    """Embedding は選択肢に混ざらない（プロバイダ方針・次元固定）。"""
    assert not [m for m in get_selectable_models() if "embedding" in m]


def test_default_model_is_selectable():
    """既定モデル自体も選択肢に含まれる（「（既定値）」と実名が一致する）。"""
    assert ModelConfig.DEFAULT_MODEL == "claude-sonnet-5"
    assert ModelConfig.DEFAULT_MODEL in get_selectable_models()


def test_config_yml_default_matches_model_config():
    """yml（経路 1）と `ModelConfig`（経路 3）の既定が食い違っていない。

    CLAUDE.md §3.1 の「解決経路は 3 本ある」への歯止め。値が割れると、
    Web 経由と CLI 経由で別モデルが走る。
    """
    from grace.config import get_config

    assert get_config().llm.model == ModelConfig.DEFAULT_MODEL


def test_light_model_path_is_unchanged():
    """判定系の軽量モデル（経路 2）は今回の変更で動かしていない。"""
    from grace.config import get_config

    assert INTENT_MODEL == "claude-haiku-4-5-20251001"
    assert get_config().llm.light_model == INTENT_MODEL


# ---------------------------------------------------------------------------
# スキーマのバリデーション（受付時に弾く）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model", EXPECTED_CHOICES)
def test_query_request_accepts_every_choice(model):
    assert QueryRequest(query="x", model=model).model == model


@pytest.mark.parametrize("empty", [None, ""])
def test_query_request_normalizes_empty_to_none(empty):
    """未選択は None（＝サーバーの既定値を使う）へ正規化する。"""
    assert QueryRequest(query="x", model=empty).model is None


@pytest.mark.parametrize(
    "model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "gemini-embedding-001", "bogus"]
)
def test_query_request_rejects_non_choices(model):
    """選択肢に無い値は受付時に弾く（ジョブ起動後の 404 にしない）。"""
    with pytest.raises(ValueError):
        QueryRequest(query="x", model=model)


def test_review_request_shares_the_same_validation():
    assert ReviewRequest(document="x", model="claude-opus-5-5").model == "claude-opus-5-5"
    with pytest.raises(ValueError):
        ReviewRequest(document="x", model="bogus")


def test_data_requests_default_to_the_new_models():
    """データ準備側の既定。チャンク化は軽量、Q/A 生成は既定モデル。"""
    assert ChunkingRequest(input_file="a/b.csv").model == "claude-haiku-4-5"
    assert QaGenerationRequest(input_file="a/b.csv").model == "claude-sonnet-5"


def test_data_requests_reject_empty_model():
    """必須フィールドなので空文字は既定へ倒さず弾く（送信側のバグを隠さない）。"""
    with pytest.raises(ValueError):
        ChunkingRequest(input_file="a/b.csv", model="")
    with pytest.raises(ValueError):
        QaGenerationRequest(input_file="a/b.csv", model="")


# ---------------------------------------------------------------------------
# メタ API
# ---------------------------------------------------------------------------


def test_get_models_lists_the_choices_with_prices():
    response = client.get("/api/models")

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == EXPECTED_CHOICES
    for row in body:
        limits = ModelConfig.get_model_limits(row["id"])
        pricing = ModelConfig.get_model_pricing(row["id"])
        assert row["input_price"] == pricing["input"]
        assert row["output_price"] == pricing["output"]
        assert row["context_window"] == limits["max_tokens"]
        assert row["max_output"] == limits["max_output"]


def test_get_model_returns_resolved_defaults():
    """「（既定値: …）」に出す実名はサーバーの解決結果から取る。"""
    response = client.get("/api/model")

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == ModelConfig.DEFAULT_MODEL
    assert body["light_model"] == INTENT_MODEL
    assert body["heavy_model"] == ""
    # Embedding は選択肢ではないが、画面の注記に実名を出すために返す（定義は ModelConfig）
    assert body["embedding_model"] == ModelConfig.EMBEDDING_MODEL
    assert body["embedding_dims"] == ModelConfig.EMBEDDING_DIMS


def test_query_endpoint_rejects_unknown_model_with_422():
    response = client.post(
        "/api/support/query", json={"query": "x", "model": "claude-sonnet-4-6"}
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# コアでの上書き
# ---------------------------------------------------------------------------


def _config_with_models():
    config = make_config_stub()
    config.llm = SimpleNamespace(
        prompt_addendum="",
        model="claude-sonnet-5",
        light_model="claude-haiku-4-5-20251001",
        heavy_model="",
    )
    return config


def _run_core_capturing_config(monkeypatch, model):
    """`run_support_agent_core` に渡った設定を捕まえる。"""
    from backend.app.core import support_agent as core

    stub = PipelineStub(config=_config_with_models())
    install_pipeline_stub(monkeypatch, stub)

    captured: dict = {}
    registry_factory = core.create_tool_registry
    monkeypatch.setattr(
        core, "create_tool_registry",
        lambda cfg: (captured.setdefault("cfg", cfg), registry_factory(cfg))[1],
    )

    core.run_support_agent_core("パスワードを忘れました", model=model)
    return captured["cfg"]


def test_core_applies_the_selected_model(monkeypatch):
    assert _run_core_capturing_config(monkeypatch, "claude-opus-5-5").llm.model == (
        "claude-opus-5-5"
    )


def test_core_keeps_light_model_when_overriding(monkeypatch):
    """⚠️ 判定系は軽量モデルのまま。

    意図分類・情報なし判定・RAG 適合性は 2 値しか返さない定型判定で、上位
    モデルを当てても精度は変わらず単価だけ上がる。`light_model` まで一緒に
    上書きすると、opus を選んだ瞬間に判定 1 回あたりの単価が 5 倍になる。
    """
    config = _run_core_capturing_config(monkeypatch, "claude-opus-5-5")

    assert config.llm.light_model == "claude-haiku-4-5-20251001"


def test_core_without_model_keeps_the_configured_default(monkeypatch):
    assert _run_core_capturing_config(monkeypatch, None).llm.model == "claude-sonnet-5"


def test_core_rejects_unknown_model(monkeypatch):
    """スキーマを通らない経路（CLI・直接呼び出し）でも弾く。"""
    with pytest.raises(ValueError, match="未対応のモデル"):
        _run_core_capturing_config(monkeypatch, "claude-sonnet-4-6")


def test_top_level_config_yml_default_matches_model_config():
    """直下 `config.yml`（経路 5）の既定が `ModelConfig` と食い違っていない。

    `services/config_service.py` がこのファイルを読み、`services/agent_service.py`
    （Legacy ReAct）は `get_config("models.default")` を既定モデルに使う。ファイルの値は
    コード側のフォールバックより優先されるため、ここが古いと旧モデルで動く
    （2026-09-24 に `claude-sonnet-4-6` のまま残っていたのを是正）。
    """
    from pathlib import Path

    import yaml

    data = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "config.yml").read_text(encoding="utf-8")
    )
    models = data["models"]
    assert models["default"] == ModelConfig.DEFAULT_MODEL
    assert set(models["available"]) <= set(ModelConfig.AVAILABLE_MODELS)
