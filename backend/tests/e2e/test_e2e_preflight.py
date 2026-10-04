"""E2E の事前確認（`conftest._preflight`）とレポートの補助のテスト。**API を呼ばないので CI でも走る。**

`_preflight` は `GRACE_E2E=1` と API キーが揃ったときにしか動かないので、
中のコードが壊れていても CI でもクラウド VM でも気づけない。

実例 2026-10-04（grace_v2_local・Mac）: 事前確認が存在しない設定値
（`ModelConfig.EMBEDDING_DIMS`）を読み、その AttributeError が「キーが無効か、
ネットワークで拒否」と表示されて 6 件すべてが ERROR になった。本リポジトリでも
同じ形で壊れうるので、Anthropic と Embedding をスタブにして事前確認そのものを通す。
"""

from types import SimpleNamespace

import pytest

from backend.tests.e2e import conftest as e2e_conftest
from config import ModelConfig


@pytest.fixture
def stub_services(monkeypatch):
    import anthropic

    import qdrant_client_wrapper

    def install(dims=ModelConfig.EMBEDDING_DIMS, anthropic_error=None):
        def models_list(**_kw):
            if anthropic_error:
                raise anthropic_error
            return []

        monkeypatch.setattr(anthropic, "Anthropic",
                            lambda *_a, **_kw: SimpleNamespace(models=SimpleNamespace(list=models_list)))
        monkeypatch.setattr(qdrant_client_wrapper, "embed_query", lambda _text: [0.0] * dims)

    return install


def test_preflight_passes_when_both_apis_work(stub_services):
    stub_services()

    e2e_conftest._preflight()


def test_preflight_fails_when_anthropic_rejects(stub_services):
    stub_services(anthropic_error=RuntimeError("401"))

    with pytest.raises(pytest.fail.Exception, match="Anthropic API を呼べない"):
        e2e_conftest._preflight()


def test_preflight_reports_wrong_dimensions_as_such(stub_services):
    """次元違いを「キーが無効」と取り違えて表示しない。"""
    stub_services(dims=768)

    with pytest.raises(pytest.fail.Exception, match="次元が 768") as exc:
        e2e_conftest._preflight()
    assert "キーが無効" not in str(exc.value)


@pytest.mark.parametrize("override", [None, "override-model"])
def test_report_records_the_model_actually_used(override):
    """レポートには実際のモデル名を残す（以前は「(config llm.model)」としか残らなかった）。"""
    from grace.config import get_config

    llm = get_config().llm
    models = e2e_conftest._resolved_models({"model": override})

    assert models == {"model": override or llm.model, "light_model": llm.light_model}
    assert "(" not in models["model"]
