"""同名 `QAPair` が 3 箇所にある事実を固定するテスト。

このリポジトリには `QAPair` という名前のクラスが 3 組あり、フィールドが違う。

| 定義場所 | 使われ方 |
|---|---|
| `models.py`（リポジトリ直下） | **現役**。`services/qa_service.py` が使う |
| `qa_generation/models.py` | `qa_generation/__init__.py` の再エクスポートのみ |
| `helper/helper_rag_qa.py` | 統合元として残る旧定義 |

**統合はしない**（2026-09-25 決定。姉妹リポジトリ `grace_v2_local` と同じ判断）。
`qa_generation.QAPair` は `__all__` に載る公開 API なので、削除も直下 `models.py` への
寄せ替えも破壊的変更になる。フィールドが違うので単純な別名にもできない。

「短く書けるから」と import 文を差し替えると、フィールドが合わずに壊れる。
どちらかのフィールドを増減させたときにこのテストが落ちるので、
**気づかないまま片側だけ変わる**ことを防げる。

`helper/helper_rag_qa.py` は `spacy` を import するため、CI（`requirements-test.txt`）では
import できない。旧定義だけは `ast` でソースを読んで確かめる。実 LLM / Qdrant 不要。
"""

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def _fields(model_cls) -> set:
    return set(model_cls.model_fields.keys())


def _legacy_qa_pair_fields() -> set:
    """`helper/helper_rag_qa.py` の `class QAPair` の注釈付きフィールド名を返す。"""
    path = _ROOT / "helper" / "helper_rag_qa.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "QAPair"]
    assert len(classes) == 1, "helper/helper_rag_qa.py に QAPair がちょうど 1 つあること"
    return {
        stmt.target.id
        for stmt in classes[0].body
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
    }


def test_top_level_and_package_qa_pair_are_distinct_classes():
    from models import QAPair as TopLevelQAPair
    from qa_generation.models import QAPair as PackageQAPair

    assert TopLevelQAPair is not PackageQAPair


def test_field_sets_differ():
    """片方にしか無いフィールドがあること（＝入れ替えると壊れること）。"""
    from models import QAPair as TopLevelQAPair
    from qa_generation.models import QAPair as PackageQAPair

    top, pkg = _fields(TopLevelQAPair), _fields(PackageQAPair)

    # 共通の土台
    assert {"question", "answer", "question_type"} <= top
    assert {"question", "answer", "question_type"} <= pkg

    # 片側にしか無いもの（入れ替え検知の要）
    assert "difficulty_level" in top and "difficulty_level" not in pkg
    assert "source_span" in pkg and "source_span" not in top
    assert "difficulty" in pkg and "difficulty" not in top


def test_legacy_definition_still_exists():
    """`helper/helper_rag_qa.py` の旧定義も残っていて、package 側と同じフィールド名を持つこと。"""
    from qa_generation.models import QAPair as PackageQAPair

    assert _legacy_qa_pair_fields() == _fields(PackageQAPair)


def test_package_qa_pair_is_reexported_as_the_public_api():
    """`qa_generation` の公開 API は package 側の定義を指す。"""
    import qa_generation
    from qa_generation.models import QAPair as PackageQAPair

    assert qa_generation.QAPair is PackageQAPair
    assert "QAPair" in qa_generation.__all__
