"""`qa_qdrant/__init__.py` に処理を書き戻していないことを固定するテスト。

## なぜ必要か

2026-09-25 まで、`qa_qdrant/__init__.py` には `make_qa.py` の古い写し（236 行）が入っていた。
パッケージの `__init__.py` はパッケージ内のどのモジュールを import しても先に実行されるため、
データ管理タブの Qdrant 登録ジョブ（`from qa_qdrant.register_to_qdrant import ...`）が
走るたびに `config` と `qa_generation.pipeline` まで読み込まれていた
（実測: `import qa_qdrant` だけで 1,406 モジュール → 修正後 35）。

経緯は `qa_generation/docs/__init__.md` §4。実 LLM / Qdrant 不要。
"""

import ast
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]


def test_qa_qdrant_init_has_only_a_docstring():
    """`qa_qdrant/__init__.py` の本体が docstring だけであること（静的検査）。"""
    path = _ROOT / "qa_qdrant" / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert ast.get_docstring(tree), "パッケージの説明（docstring）は残すこと"
    assert len(tree.body) == 1, "docstring 以外の文（import・関数・代入など）を置かないこと"


def test_importing_qa_qdrant_does_not_pull_qa_generation():
    """`import qa_qdrant` で `qa_generation` / `config` が読み込まれないこと。"""
    code = (
        "import sys\n"
        "import qa_qdrant  # noqa: F401\n"
        "print(','.join(sorted(m for m in ('qa_generation', 'config') if m in sys.modules)))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=300, cwd=_ROOT,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == ""
