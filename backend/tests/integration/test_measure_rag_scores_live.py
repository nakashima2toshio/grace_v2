"""`scripts/measure_rag_scores.py::measure` を実 Qdrant で流す結合テスト。

Embedding API は呼ばない（質問ごとに固定ベクトルを返すスタブ）。実 Qdrant の
`search_collection` が返すスコアを、許可コレクションの中で最大のものとして拾えるかを見る。
共用 Qdrant を壊さないよう、`grace_it_` のコレクションだけを使う。
"""

from types import SimpleNamespace

import pytest
from qdrant_client.http import models

import qdrant_client_wrapper as wrapper
from backend.tests.integration.conftest import QDRANT_URL
from scripts import measure_rag_scores

pytestmark = pytest.mark.integration


def test_measure_takes_the_best_score_across_allowed_collections(qdrant_client, temp_collection, monkeypatch):
    qdrant_client.create_collection(
        temp_collection, vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE))
    qdrant_client.upsert(temp_collection, points=[
        models.PointStruct(id=1, vector=[1.0, 0.0], payload={"answer": "住民票は 300 円"}),
    ])
    vectors = {"同じ向き": [1.0, 0.0], "45度": [1.0, 1.0], "直交": [0.0, 1.0]}
    monkeypatch.setattr(wrapper, "embed_query", lambda q: vectors[q])
    monkeypatch.setattr(wrapper, "embed_sparse_query_unified",
                        lambda q: (_ for _ in ()).throw(RuntimeError("sparse なし")))
    profiles = {"gov": SimpleNamespace(collections=[temp_collection, "grace_it_does_not_exist"])}

    rows = measure_rag_scores.measure(
        [("gov", "in", "同じ向き"), ("gov", "in", "45度"), ("gov", "out", "直交")], profiles, QDRANT_URL)

    tops = {r["query"]: r["top"] for r in rows}
    assert tops["同じ向き"] == pytest.approx(1.0, abs=1e-4)
    assert tops["45度"] == pytest.approx(0.7071, abs=1e-3)
    assert tops["直交"] == pytest.approx(0.0, abs=1e-4)
    assert {r["collection"] for r in rows if r["top"] > 0} == {temp_collection}
