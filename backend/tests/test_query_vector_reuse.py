# backend/tests/test_query_vector_reuse.py
"""**同じクエリを何度も埋め込まない**ことを固定するテスト。

## 背景（実測 2026-08-17 11:41）

`search_rag_knowledge_base_structured` は `precomputed_*` を渡さないと呼び出し
ごとにクエリを埋め込み直す。`RAGSearchTool.execute` は全コレクションを順に舐める
ループなので、**1 質問あたりコレクション数ぶんの Embedding API 呼び出し**が
発生していた。

    11:41:47 → 11:41:51  batchEmbedContents ×7（すべて同一クエリ）  約 4 秒

クエリベクトルはコレクションに依存しないので、結果は 7 回とも同じ。外部 API
（Gemini）なので待ち時間だけでなく**課金にも効く**。

## 失敗しても検索は止めない

事前埋め込みに失敗したら `None` を返し、下位が従来どおりコレクションごとに
埋め込む（＝この最適化が無い状態へ戻るだけ）。検索そのものは continue する。

ここで固定すること:
  1. 複数コレクションでも埋め込みは 1 回だけ
  2. 事前計算したベクトルが実際に検索へ渡ること
  3. 失敗しても検索が続くこと（劣化動作）
  4. sparse だけ失敗しても dense は使われること
  5. 1 コレクションなら下位へ任せること（経路を増やさない）

⚠️ Qdrant にも Gemini にも接続しない。
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from grace.tools import RAGSearchTool

COLLECTIONS = ["gov_faq_anthropic", "gov_laws_anthropic", "ec_faq_anthropic"]
DENSE = [0.1] * 3072
SPARSE = SimpleNamespace(indices=[1, 2], values=[0.5, 0.5])


@pytest.fixture()
def tool():
    t = RAGSearchTool.__new__(RAGSearchTool)
    t.config = SimpleNamespace(
        qdrant=SimpleNamespace(
            url="http://localhost:6333",
            collection_name="dummy",
            restrict_to_collection=False,
            allowed_collections=[],
            excluded_collections=[],
        ),
        executor=SimpleNamespace(reasoning_min_rag_score=0.64),
    )
    t.keyword_extractor = None
    return t


@pytest.fixture()
def wired(monkeypatch):
    """埋め込み呼び出しと検索呼び出しを記録する。"""
    calls = {"dense": [], "sparse": [], "search": []}

    def _dense(q):
        calls["dense"].append(q)
        return DENSE

    def _sparse(q):
        calls["sparse"].append(q)
        return SPARSE

    def _search(q, col, **kwargs):
        calls["search"].append((col, kwargs))
        return []

    monkeypatch.setattr("qdrant_client_wrapper.embed_query", _dense, raising=False)
    monkeypatch.setattr(
        "qdrant_client_wrapper.embed_sparse_query_unified", _sparse, raising=False
    )
    monkeypatch.setattr(
        "agent_tools.search_rag_knowledge_base_structured", _search
    )
    monkeypatch.setattr(
        RAGSearchTool, "_get_all_collections_dynamic", lambda _s: list(COLLECTIONS)
    )
    return calls


# =============================================================================
# ① 1 回だけ埋め込む
# =============================================================================

class TestEmbeddedOnce:

    def test_dense_is_computed_once_for_many_collections(self, tool, wired):
        tool.execute(query="住民票の写しの取り方は？")

        assert len(wired["search"]) == len(COLLECTIONS), "全コレクションを検索している"
        assert len(wired["dense"]) == 1, (
            f"クエリを {len(wired['dense'])} 回埋め込んでいる"
            "（コレクション数ぶん API を叩いている）"
        )

    def test_sparse_is_computed_once(self, tool, wired):
        tool.execute(query="住民票の写しの取り方は？")

        assert len(wired["sparse"]) == 1

    def test_precomputed_vectors_reach_the_search(self, tool, wired):
        tool.execute(query="住民票の写しの取り方は？")

        for _col, kwargs in wired["search"]:
            assert kwargs["precomputed_query_vector"] is DENSE
            assert kwargs["precomputed_sparse_vector"] is SPARSE

    def test_single_collection_delegates_downstream(self, tool, wired, monkeypatch):
        """1 コレクションなら下位に任せる（経路を増やさない）。"""
        monkeypatch.setattr(
            RAGSearchTool, "_get_all_collections_dynamic", lambda _s: ["gov_faq_anthropic"]
        )

        tool.execute(query="住民票の写しの取り方は？")

        assert wired["dense"] == [], "1 件なら事前計算しない"
        [(_col, kwargs)] = wired["search"]
        assert "precomputed_query_vector" not in kwargs


# =============================================================================
# ② 失敗しても検索は止めない（劣化動作）
# =============================================================================

class TestDegradesGracefully:

    def test_dense_failure_still_searches(self, tool, wired, monkeypatch, caplog):
        def _boom(_q):
            raise RuntimeError("Gemini API unavailable")

        monkeypatch.setattr("qdrant_client_wrapper.embed_query", _boom, raising=False)

        with caplog.at_level(logging.WARNING):
            result = tool.execute(query="住民票の写しの取り方は？")

        assert len(wired["search"]) == len(COLLECTIONS), "検索が止まっている"
        assert "コレクションごとに再計算します" in caplog.text
        for _col, kwargs in wired["search"]:
            assert kwargs == {}, "作れなかったベクトルを渡してはいけない"
        assert result is not None

    def test_sparse_failure_keeps_dense(self, tool, wired, monkeypatch):
        """sparse は任意。失敗しても dense は使う（従来どおり dense 検索へ倒れる）。"""
        def _boom(_q):
            raise RuntimeError("sparse model missing")

        monkeypatch.setattr(
            "qdrant_client_wrapper.embed_sparse_query_unified", _boom, raising=False
        )

        tool.execute(query="住民票の写しの取り方は？")

        assert len(wired["dense"]) == 1
        for _col, kwargs in wired["search"]:
            assert kwargs["precomputed_query_vector"] is DENSE
            assert "precomputed_sparse_vector" not in kwargs


# =============================================================================
# ③ ヘルパ単体
# =============================================================================

class TestEmbedQueryOnce:

    def test_returns_both_vectors(self, tool, wired):
        assert tool._embed_query_once("質問", 3) == (DENSE, SPARSE)

    def test_single_collection_returns_none(self, tool, wired):
        assert tool._embed_query_once("質問", 1) == (None, None)
        assert wired["dense"] == []

    def test_zero_collections_returns_none(self, tool, wired):
        assert tool._embed_query_once("質問", 0) == (None, None)

    def test_logs_the_reuse_count(self, tool, wired, caplog):
        with caplog.at_level(logging.INFO):
            tool._embed_query_once("質問", 7)

        assert "7 コレクションで再利用" in caplog.text
