"""`scripts/qdrant_snapshot.py` の export → restore を実 Qdrant で往復させる結合テスト。

E2E の実データは Mac の Qdrant からこの経路で VM へ運ぶ（`backend/docs/testing.md` §1.2）。
往復で点数・ペイロードが変わらないこと、既存を上書きしないこと、
壊れた / 合わないアーカイブを拒否することを確かめる。
"""

import functools
import http.server
import importlib.util
import io
import json
import tarfile
import threading
from pathlib import Path

import pytest
from qdrant_client.http import models

from backend.tests.integration.conftest import QDRANT_URL

pytestmark = pytest.mark.integration

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "qdrant_snapshot.py"


def _load():
    spec = importlib.util.spec_from_file_location("qdrant_snapshot", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qs = _load()
N = 5


@pytest.fixture
def filled(qdrant_client, temp_collection):
    qdrant_client.create_collection(
        temp_collection, vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE)
    )
    qdrant_client.upsert(temp_collection, [
        models.PointStruct(id=i, vector=[1.0, float(i), 0.0, 0.0], payload={"question": f"q{i}"})
        for i in range(N)
    ])
    return temp_collection


@pytest.fixture
def archive(filled, tmp_path):
    out = tmp_path / "grace_e2e_snapshot.tar.gz"
    qs.export_snapshots(QDRANT_URL, [filled], out)
    return out


def _count(client, name):
    return client.count(name, exact=True).count


def test_export_records_manifest_and_cleans_server(qdrant_client, filled, tmp_path):
    out = tmp_path / "a.tar.gz"

    manifest = qs.export_snapshots(QDRANT_URL, [filled, "grace_it_absent"], out)

    [entry] = manifest["collections"]
    assert entry["name"] == filled and entry["points_count"] == N
    assert manifest["missing"] == ["grace_it_absent"]
    assert manifest["embedding"] == qs.embedding_model()
    # 作成したスナップショットを Qdrant 側に残さない
    assert qdrant_client.list_snapshots(filled) == []


def test_restore_from_file_reproduces_points(qdrant_client, filled, archive):
    qdrant_client.delete_collection(filled)

    outcome = qs.restore_snapshots(QDRANT_URL, str(archive))

    assert outcome[filled] == f"restored:{N:,} 点"
    assert _count(qdrant_client, filled) == N
    assert qdrant_client.retrieve(filled, [3])[0].payload == {"question": "q3"}


def test_restore_from_url(qdrant_client, filled, archive):
    """署名付き URL 相当（HTTP でダウンロード）でも復元できる。"""
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(archive.parent))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    qdrant_client.delete_collection(filled)
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/{archive.name}"
        outcome = qs.restore_snapshots(QDRANT_URL, url)
    finally:
        server.shutdown()

    assert outcome[filled].startswith("restored:")
    assert _count(qdrant_client, filled) == N


def test_existing_collection_is_not_overwritten_without_force(qdrant_client, filled, archive):
    qdrant_client.delete(filled, points_selector=models.PointIdsList(points=[0, 1]))

    outcome = qs.restore_snapshots(QDRANT_URL, str(archive))

    assert outcome[filled].startswith("skipped:既存")
    assert _count(qdrant_client, filled) == N - 2


def test_force_overwrites_existing_collection(qdrant_client, filled, archive):
    qdrant_client.delete(filled, points_selector=models.PointIdsList(points=[0, 1]))

    qs.restore_snapshots(QDRANT_URL, str(archive), force=True)

    assert _count(qdrant_client, filled) == N


def test_refuses_snapshot_from_another_embedding_model(qdrant_client, filled, archive, monkeypatch):
    qdrant_client.delete_collection(filled)
    monkeypatch.setattr(qs, "embedding_model", lambda: {"model": "other-embedding", "dims": 768})

    with pytest.raises(qs.SnapshotError, match="Embedding モデルが違います"):
        qs.restore_snapshots(QDRANT_URL, str(archive))
    assert not qdrant_client.collection_exists(filled)


def test_refuses_tampered_snapshot(qdrant_client, filled, archive, tmp_path):
    with tarfile.open(archive, "r:gz") as tar:
        manifest = tar.extractfile("manifest.json").read()
    tampered = tmp_path / "tampered.tar.gz"
    with tarfile.open(tampered, "w:gz") as tar:
        for name, data in {"manifest.json": manifest, f"{filled}.snapshot": b"not a snapshot"}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    qdrant_client.delete_collection(filled)

    with pytest.raises(qs.SnapshotError, match="sha256"):
        qs.restore_snapshots(QDRANT_URL, str(tampered))
    assert json.loads(manifest)["collections"][0]["name"] == filled
