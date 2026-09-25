"""`qa_qdrant/make_qa_register_qdrant.py` の終了コードを固定するテスト。

2026-09-25 まで、Phase 2（Qdrant 登録）の `run_registration()` が `False` を返しても、
`main()` はエラーログを出すだけで**終了コード 0** で終わっていた。シェルスクリプトや
ジョブ管理から失敗を検知できないため、失敗時は終了コード 1 で止めるよう直した
（経緯は `qa_qdrant/docs/make_qa_register_qdrant_ipo.md` §3.3）。

`question` / `answer` 列を持つ CSV を渡すと Phase 1（Q/A 生成）を飛ばすので、
`run_registration` をモックに差し替えれば実 LLM / Qdrant / API キーなしで `main()` を通せる。
"""

import sys

import pytest

import qa_qdrant.make_qa_register_qdrant as mqr


@pytest.fixture
def qa_csv(tmp_path):
    path = tmp_path / "qa.csv"
    path.write_text("question,answer\n富士山の高さは？,3776メートル\n", encoding="utf-8")
    return path


def _run_main(monkeypatch, qa_csv, tmp_path, registration_result):
    calls = []

    def fake_registration(**kwargs):
        calls.append(kwargs)
        return registration_result

    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    monkeypatch.setattr(mqr, "run_registration", fake_registration)
    monkeypatch.setattr(sys, "argv", [
        "make_qa_register_qdrant.py",
        "--input-file", str(qa_csv),
        "--collection", "tmp_collection",
        "--ui-output", str(tmp_path / "ui"),
    ])
    mqr.main()
    return calls


def test_registration_failure_exits_with_1(monkeypatch, qa_csv, tmp_path):
    """Qdrant 登録が失敗したら終了コード 1 で止まること。"""
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, qa_csv, tmp_path, registration_result=False)
    assert exc.value.code == 1


def test_registration_success_returns_normally(monkeypatch, qa_csv, tmp_path):
    """登録が成功したら例外なく戻る（終了コード 0）。Q/A 済み CSV はそのまま登録に渡る。"""
    calls = _run_main(monkeypatch, qa_csv, tmp_path, registration_result=True)
    assert len(calls) == 1
    assert calls[0]["csv_path"] == str(qa_csv)
    assert calls[0]["collection_name"] == "tmp_collection"
