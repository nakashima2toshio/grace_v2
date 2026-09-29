"""Qdrant に接続できないとき、RAG 検索は何もせず即失敗することを守るテスト。

## なぜ必要か

以前は、コレクション一覧を取れなくても既定の候補（優先順位リスト）へ倒れて検索を続け、
クエリの Embedding（Gemini API）と Sparse モデルの読み込み（初回は 500MB 超の
ダウンロード）を済ませたうえで、候補コレクションの数だけ接続エラーを繰り返していた
（実測 2026-09-29: 約 4 秒の無駄）。どうせ全部失敗するので、即失敗にして
executor の fallback（Web 検索）へ進ませる。
"""


import pytest

import agent_tools
from grace.config import get_config
from grace.tools import RAGSearchTool


class _DownClient:
    def get_collections(self):
        raise ConnectionRefusedError(61, "Connection refused")


class _BrokenClient:
    def get_collections(self):
        raise RuntimeError("unexpected server error")


@pytest.fixture(autouse=True)
def _clear_cache():
    RAGSearchTool.clear_collections_cache()
    yield
    RAGSearchTool.clear_collections_cache()


def _tool(client) -> RAGSearchTool:
    tool = RAGSearchTool(config=get_config())
    tool._client = client
    return tool


def test_unreachable_qdrant_fails_fast_without_embedding_or_search(monkeypatch):
    tool = _tool(_DownClient())

    def must_not_embed(*_a, **_k):
        raise AssertionError("到達不能なのにクエリの Embedding を呼んだ")

    def must_not_search(*_a, **_k):
        raise AssertionError("到達不能なのにコレクション検索を呼んだ")

    monkeypatch.setattr(tool, "_embed_query_once", must_not_embed)
    monkeypatch.setattr(agent_tools, "search_rag_knowledge_base_structured", must_not_search)

    result = tool.execute(query="住民票の写しの取り方は？")

    assert result.success is False
    assert result.output == []
    assert "Qdrant に接続できません" in result.error
    assert "docker compose" in result.error  # 起動コマンドの案内を添える
    assert result.confidence_factors["result_count"] == 0


def test_dynamic_collections_returns_none_only_when_unreachable():
    assert _tool(_DownClient())._get_all_collections_dynamic() is None


def test_other_errors_still_fall_back_to_the_default_candidates():
    """接続エラー以外は従来どおり既定の候補へ倒れる（None にしない）。"""
    result = _tool(_BrokenClient())._get_all_collections_dynamic()

    assert isinstance(result, list)
    assert result  # search_priority から作った既定の候補
