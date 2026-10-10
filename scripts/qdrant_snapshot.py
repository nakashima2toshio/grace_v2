#!/usr/bin/env python3
"""E2E 用に、Qdrant の実データコレクションをスナップショットで持ち運ぶ。

## なぜ必要か

GRACE-Support / GRACE-Review の E2E（`tests/e2e/`）は、Mac の Qdrant に
登録済みの**実データ**（`gov_faq_anthropic` など）を検索して初めて意味を持つ。
ところが Support 用データの元 CSV はリポジトリに無く（各自で用意する）、
クラウド VM（Claude Code on the web）の Qdrant は空である。

そこで Mac の Qdrant から**スナップショット**（ベクトル込みの丸ごとの複製）を
取り、VM で復元する。Embedding をやり直さないので費用も時間もかからず、
**Mac と同じベクトル**で検索できる。

## 使い方

```bash
# 対象コレクションと Qdrant 上の状態を表示する
python scripts/qdrant_snapshot.py list

# ① Mac: スナップショットを 1 つの tar.gz にまとめる（既定 grace_e2e_snapshot.tar.gz）
python scripts/qdrant_snapshot.py export

# ② Mac: できたファイルを非公開の保存先へ置き、署名付き URL を発行する
#    （例: gcloud storage sign-url / aws s3 presign）

# ③ VM: 環境変数 GRACE_E2E_SNAPSHOT_URL にその URL を設定しておくと、
#    SessionStart hook が自動で restore する。手で流すなら:
python scripts/qdrant_snapshot.py restore --source "$GRACE_E2E_SNAPSHOT_URL"
```

## 対象コレクション

既定は `verticals.py` の `PROFILES[*].collections` と `rulesets.py` の
`RULESETS[*].collections` / `RuleItem.evidence_collections` の和集合
（＝アプリが実際に検索するもの）。**ここに名前を書き写さない**（増えたら自動で追随する）。
`--collections a,b` で絞れる。

## 安全策

- `restore` は、**点が入っている既存コレクションを上書きしない**（`--force` で上書き）。
  Mac の Qdrant は grace_v2_local と共用なので、誤って流しても壊さないため。
- `export` 時の Embedding モデル（`config.ModelConfig.EMBEDDING_MODEL`）を manifest に記録し、
  `restore` 側と違えば**拒否する**。モデルが違うとエラーにならずに検索結果だけが壊れる
  （CLAUDE.md §3）。
- ファイルごとに sha256 を記録し、復元前に照合する。
- tar の中身は manifest.json と `*.snapshot` だけを受け付ける（パスを含む名前は拒否）。
- 生成物 `grace_e2e_snapshot*.tar.gz` は `.gitignore` 済み（データを git に入れない）。

## 前提

- Qdrant の REST API（既定 `config.QdrantConfig.URL`。`--qdrant-url` / `QDRANT_URL` で変更可）
- `httpx`（requirements-test.txt に含まれる）
- スナップショットは**作成した Qdrant と同じか新しい版**で復元する。VM は
  `qdrant/qdrant:latest` なので、Mac 側が古くても通常は問題ない。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_ARCHIVE = Path("grace_e2e_snapshot.tar.gz")
MANIFEST = "manifest.json"
# スナップショットの作成・転送は大きなコレクションで数分かかる
LONG_TIMEOUT = httpx.Timeout(connect=10.0, read=None, write=None, pool=None)


class SnapshotError(RuntimeError):
    pass


# ----------------------------------------------------------------------
# 対象コレクション（アプリの定義から集める）
# ----------------------------------------------------------------------
def required_collections() -> List[str]:
    """アプリが検索するコレクション名（重複なし・定義順）。"""
    from backend.app.core.rulesets import RULESETS
    from backend.app.core.verticals import PROFILES

    names: List[str] = []
    for profile in PROFILES.values():
        names.extend(profile.collections)
    for ruleset in RULESETS.values():
        names.extend(ruleset.collections)
        for rule in ruleset.rules:
            names.extend(rule.evidence_collections)
    return list(dict.fromkeys(names))


def default_qdrant_url() -> str:
    from config import QdrantConfig

    return os.getenv("QDRANT_URL", QdrantConfig.URL)


def embedding_model() -> Dict[str, object]:
    from config import ModelConfig

    return {"model": ModelConfig.EMBEDDING_MODEL, "dims": ModelConfig.EMBEDDING_DIMS}


# ----------------------------------------------------------------------
# Qdrant REST
# ----------------------------------------------------------------------
class Qdrant:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.http = httpx.Client(base_url=self.url, timeout=30.0)

    def version(self) -> str:
        return self.http.get("/").json().get("version", "unknown")

    def points_count(self, name: str) -> Optional[int]:
        """コレクションの点数。無ければ None。"""
        r = self.http.get(f"/collections/{name}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        # 0 件のときは points_count が null で返る版がある
        return r.json()["result"].get("points_count") or 0

    def exact_count(self, name: str) -> int:
        r = self.http.post(f"/collections/{name}/points/count", json={"exact": True})
        r.raise_for_status()
        return r.json()["result"]["count"]

    def create_snapshot(self, name: str) -> str:
        r = self.http.post(f"/collections/{name}/snapshots", params={"wait": "true"},
                           timeout=LONG_TIMEOUT)
        r.raise_for_status()
        return r.json()["result"]["name"]

    def download_snapshot(self, name: str, snapshot: str, dest: Path) -> None:
        with self.http.stream("GET", f"/collections/{name}/snapshots/{snapshot}",
                              timeout=LONG_TIMEOUT) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)

    def delete_snapshot(self, name: str, snapshot: str) -> None:
        self.http.delete(f"/collections/{name}/snapshots/{snapshot}")

    def upload_snapshot(self, name: str, path: Path) -> None:
        with open(path, "rb") as f:
            r = self.http.post(
                f"/collections/{name}/snapshots/upload",
                params={"priority": "snapshot", "wait": "true"},
                files={"snapshot": (path.name, f, "application/octet-stream")},
                timeout=LONG_TIMEOUT,
            )
        if r.status_code >= 400:
            raise SnapshotError(f"{name}: 復元に失敗しました（HTTP {r.status_code}）: {r.text[:300]}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_collections(arg: Optional[str]) -> List[str]:
    if not arg:
        return required_collections()
    return [c.strip() for c in arg.split(",") if c.strip()]


# ----------------------------------------------------------------------
# list
# ----------------------------------------------------------------------
def cmd_list(args) -> int:
    q = Qdrant(args.qdrant_url)
    print(f"Qdrant: {q.url}（{q.version()}）")
    for name in _parse_collections(args.collections):
        n = q.points_count(name)
        print(f"  {name:28s} {'（無し）' if n is None else f'{n:,} 点'}")
    return 0


# ----------------------------------------------------------------------
# export
# ----------------------------------------------------------------------
def export_snapshots(qdrant_url: str, collections: List[str], out: Path) -> Dict:
    q = Qdrant(qdrant_url)
    manifest: Dict = {
        "format": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qdrant_version": q.version(),
        "embedding": embedding_model(),
        "collections": [],
        "missing": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for name in collections:
            count = q.points_count(name)
            if count is None:
                print(f"  - {name}: Qdrant に無いので飛ばします")
                manifest["missing"].append(name)
                continue
            print(f"  - {name}: {count:,} 点のスナップショットを作成中…")
            snapshot = q.create_snapshot(name)
            dest = tmpdir / f"{name}.snapshot"
            try:
                q.download_snapshot(name, snapshot, dest)
            finally:
                # Qdrant のディスクに残さない
                q.delete_snapshot(name, snapshot)
            manifest["collections"].append({
                "name": name,
                "file": dest.name,
                "points_count": q.exact_count(name),
                "size": dest.stat().st_size,
                "sha256": _sha256(dest),
            })
        if not manifest["collections"]:
            raise SnapshotError("書き出せるコレクションがありません（すべて Qdrant に無い）")
        (tmpdir / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(out, "w:gz") as tar:
            tar.add(tmpdir / MANIFEST, arcname=MANIFEST)
            for c in manifest["collections"]:
                tar.add(tmpdir / c["file"], arcname=c["file"])
    return manifest


def cmd_export(args) -> int:
    out = Path(args.out)
    manifest = export_snapshots(args.qdrant_url, _parse_collections(args.collections), out)
    total = sum(c["points_count"] for c in manifest["collections"])
    print(f"\n✅ {out}（{out.stat().st_size / 1e6:.1f} MB・{len(manifest['collections'])} コレクション・{total:,} 点）")
    if manifest["missing"]:
        print(f"⚠️ 無かったコレクション: {', '.join(manifest['missing'])}"
              "（それを使う E2E は skip される）")
    print("次: このファイルを非公開の保存先へ置き、署名付き URL を GRACE_E2E_SNAPSHOT_URL に設定する")
    return 0


# ----------------------------------------------------------------------
# restore
# ----------------------------------------------------------------------
def _fetch(source: str, workdir: Path) -> Path:
    """URL ならダウンロード、パスならそのまま返す。"""
    if source.startswith(("http://", "https://")):
        dest = workdir / "snapshot.tar.gz"
        with httpx.stream("GET", source, follow_redirects=True, timeout=LONG_TIMEOUT) as r:
            if r.status_code >= 400:
                # 署名付き URL の期限切れは 400 / 403 で返ることが多い
                raise SnapshotError(
                    f"ダウンロードに失敗しました（HTTP {r.status_code}）。"
                    "署名付き URL なら期限切れの可能性があります"
                )
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
        return dest
    path = Path(source).expanduser()
    if not path.is_file():
        raise SnapshotError(f"ファイルがありません: {path}")
    return path


def _safe_extract(archive: Path, workdir: Path) -> Dict:
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if (not member.isfile() or "/" in name or "\\" in name or name.startswith(".")
                    or not (name == MANIFEST or name.endswith(".snapshot"))):
                raise SnapshotError(f"想定外のファイルが含まれています: {name!r}")
            tar.extract(member, workdir, filter="data")
    manifest_path = workdir / MANIFEST
    if not manifest_path.exists():
        raise SnapshotError("manifest.json がありません（export で作ったファイルか確認してください）")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def restore_snapshots(qdrant_url: str, source: str, only: Optional[List[str]] = None,
                      force: bool = False) -> Dict[str, str]:
    """復元し、コレクションごとの結果（restored / skipped:... ）を返す。"""
    q = Qdrant(qdrant_url)
    outcome: Dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        manifest = _safe_extract(_fetch(source, workdir), workdir)

        expected = embedding_model()
        if manifest.get("embedding") != expected:
            raise SnapshotError(
                f"Embedding モデルが違います（スナップショット: {manifest.get('embedding')} / "
                f"このリポジトリ: {expected}）。ベクトルの意味が合わず検索結果が壊れるので復元しません"
            )

        for entry in manifest["collections"]:
            name = entry["name"]
            if only and name not in only:
                continue
            existing = q.points_count(name)
            if existing and not force:
                outcome[name] = f"skipped:既存（{existing:,} 点）"
                continue
            path = workdir / entry["file"]
            if _sha256(path) != entry["sha256"]:
                raise SnapshotError(f"{name}: sha256 が一致しません（ファイルが壊れています）")
            q.upload_snapshot(name, path)
            got = q.exact_count(name)
            if got != entry["points_count"]:
                raise SnapshotError(f"{name}: 復元後の点数 {got} が記録 {entry['points_count']} と違います")
            outcome[name] = f"restored:{got:,} 点"
        for name in manifest.get("missing", []):
            outcome.setdefault(name, "skipped:export 時に無かった")
    return outcome


def cmd_restore(args) -> int:
    source = args.source or os.getenv("GRACE_E2E_SNAPSHOT_URL")
    if not source:
        print("❌ --source か GRACE_E2E_SNAPSHOT_URL を指定してください", file=sys.stderr)
        return 2
    only = _parse_collections(args.collections) if args.collections else None
    outcome = restore_snapshots(args.qdrant_url, source, only=only, force=args.force)
    for name, status in outcome.items():
        print(f"  {name:28s} {status}")
    return 0


# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="E2E 用 Qdrant スナップショットの書き出し・復元")
    parser.add_argument("--qdrant-url", default=None, help="既定: QDRANT_URL または config.QdrantConfig.URL")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="対象コレクションと状態を表示する")
    p.add_argument("--collections", help="カンマ区切り（既定: アプリが検索するもの全部）")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("export", help="スナップショットを tar.gz にまとめる（Mac で使う）")
    p.add_argument("--collections", help="カンマ区切り（既定: アプリが検索するもの全部）")
    p.add_argument("--out", default=str(DEFAULT_ARCHIVE), help=f"出力先（既定: {DEFAULT_ARCHIVE}）")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("restore", help="tar.gz を Qdrant へ復元する（VM で使う）")
    p.add_argument("--source", help="URL またはファイルパス（既定: GRACE_E2E_SNAPSHOT_URL）")
    p.add_argument("--collections", help="カンマ区切り（既定: tar.gz に入っているもの全部）")
    p.add_argument("--force", action="store_true", help="点が入っている既存コレクションも上書きする")
    p.set_defaults(func=cmd_restore)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    args.qdrant_url = args.qdrant_url or default_qdrant_url()
    try:
        return args.func(args)
    except SnapshotError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except httpx.HTTPError as e:
        print(f"❌ Qdrant / ダウンロードとの通信に失敗しました: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

