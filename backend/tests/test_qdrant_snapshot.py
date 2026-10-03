"""E2E 用スナップショット（`scripts/qdrant_snapshot.py`）のうち Qdrant を使わない部分のテスト。

実 Qdrant を使う往復（export → restore）は `integration/test_qdrant_snapshot_live.py`。
"""

import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest

from backend.app.core.rulesets import RULESETS
from backend.app.core.verticals import PROFILES

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "qdrant_snapshot.py"


def _load():
    """`scripts/` はパッケージではないのでファイルから直接読み込む。"""
    spec = importlib.util.spec_from_file_location("qdrant_snapshot", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


qs = _load()


class TestRequiredCollections:
    def test_covers_every_collection_the_app_searches(self):
        expected = set()
        for profile in PROFILES.values():
            expected |= set(profile.collections)
        for ruleset in RULESETS.values():
            expected |= set(ruleset.collections)
            for rule in ruleset.rules:
                expected |= set(rule.evidence_collections)

        names = qs.required_collections()

        assert set(names) == expected
        assert len(names) == len(set(names))  # 重複なし
        assert {"gov_faq_anthropic", "ec_ad_rules_anthropic", "ec_policy_anthropic"} <= set(names)


def _tar(tmp_path, members):
    path = tmp_path / "in.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


class TestSafeExtract:
    MANIFEST = json.dumps({"collections": []}).encode()

    def test_accepts_manifest_and_snapshots(self, tmp_path):
        archive = _tar(tmp_path, {"manifest.json": self.MANIFEST, "a.snapshot": b"x"})
        out = tmp_path / "out"
        out.mkdir()

        assert qs._safe_extract(archive, out) == {"collections": []}
        assert (out / "a.snapshot").read_bytes() == b"x"

    @pytest.mark.parametrize("bad", ["../evil.snapshot", "dir/a.snapshot", ".hidden.snapshot", "run.sh"])
    def test_rejects_unexpected_members(self, tmp_path, bad):
        archive = _tar(tmp_path, {"manifest.json": self.MANIFEST, bad: b"x"})
        out = tmp_path / "out"
        out.mkdir()

        with pytest.raises(qs.SnapshotError, match="想定外のファイル"):
            qs._safe_extract(archive, out)
        assert not (tmp_path / "evil.snapshot").exists()

    def test_requires_manifest(self, tmp_path):
        archive = _tar(tmp_path, {"a.snapshot": b"x"})
        out = tmp_path / "out"
        out.mkdir()

        with pytest.raises(qs.SnapshotError, match="manifest.json"):
            qs._safe_extract(archive, out)


class TestCli:
    def test_restore_without_source_is_an_error(self, monkeypatch, capsys):
        monkeypatch.delenv("GRACE_E2E_SNAPSHOT_URL", raising=False)

        assert qs.main(["--qdrant-url", "http://127.0.0.1:9", "restore"]) == 2
        assert "GRACE_E2E_SNAPSHOT_URL" in capsys.readouterr().err

    def test_missing_file_is_reported_not_raised(self, tmp_path, capsys):
        code = qs.main(["--qdrant-url", "http://127.0.0.1:9", "restore", "--source", str(tmp_path / "nope.tar.gz")])

        assert code == 1
        assert "ファイルがありません" in capsys.readouterr().err
