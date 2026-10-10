"""`qa_qdrant/make_qa_register_qdrant.py` の起動時チェックを固定するテスト。

2026-09-25 まで次の 2 つが食い違っていた（経緯は `qa_qdrant/docs/make_qa_register_qdrant_ipo.md` §3.3）。

- `ANTHROPIC_API_KEY` を確かめるのは `.txt` 入力のチャンク化だけで、チャンク済み CSV や
  `--dataset` からの Q/A 生成は、キーが無くても LLM を最初に呼ぶまで失敗しなかった。
  → Q/A 生成の前に確かめて終了コード 1 で止める。Q/A 済み CSV の登録だけならキーは要らない。
- `--provider` は受け取るだけで使われず、何を指定しても Gemini で Embedding していた。
  → `choices=["gemini"]` にして、他の値は argparse が終了コード 2 で拒否する。

Q/A 生成・登録は差し替えるので、実 LLM / Qdrant / API キーは不要。
"""

import sys

import pytest

import qa_qdrant.make_qa_register_qdrant as mqr


class _FakePipeline:
    """`QAPipeline` の代わり。生成されたら記録する（キー不足で止まるなら生成されない）。"""

    instances = []

    def __init__(self, **kwargs):
        _FakePipeline.instances.append(kwargs)

    def run(self, **kwargs):  # pragma: no cover - キー不足のテストでは呼ばれない
        raise AssertionError("run() は呼ばれない想定")


@pytest.fixture
def env(monkeypatch):
    calls = {"registration": []}

    def fake_registration(**kwargs):
        calls["registration"].append(kwargs)
        return True

    _FakePipeline.instances = []
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(mqr, "QAPipeline", _FakePipeline)
    monkeypatch.setattr(mqr, "run_registration", fake_registration)
    return calls


def _argv(monkeypatch, tmp_path, *args):
    monkeypatch.setattr(sys, "argv", [
        "make_qa_register_qdrant.py",
        "--collection", "tmp_collection",
        "--output", str(tmp_path / "qa"),
        "--ui-output", str(tmp_path / "ui"),
        *args,
    ])


def test_chunk_csv_without_anthropic_key_exits_with_1(monkeypatch, tmp_path, env):
    """チャンク済み CSV から Q/A を生成するとき、キーが無ければ生成前に終了コード 1。"""
    csv = tmp_path / "chunks.csv"
    csv.write_text("text\n富士山は日本で最も高い山である。\n", encoding="utf-8")
    _argv(monkeypatch, tmp_path, "--input-file", str(csv))

    with pytest.raises(SystemExit) as exc:
        mqr.main()
    assert exc.value.code == 1
    assert _FakePipeline.instances == []
    assert env["registration"] == []


def test_dataset_without_anthropic_key_exits_with_1(monkeypatch, tmp_path, env):
    """`--dataset` から Q/A を生成するとき、キーが無ければ生成前に終了コード 1。"""
    _argv(monkeypatch, tmp_path, "--dataset", "cc_news")

    with pytest.raises(SystemExit) as exc:
        mqr.main()
    assert exc.value.code == 1
    assert _FakePipeline.instances == []
    assert env["registration"] == []


def test_qa_csv_does_not_need_anthropic_key(monkeypatch, tmp_path, env):
    """Q/A 済み CSV の登録だけなら `ANTHROPIC_API_KEY` なしで通る。"""
    csv = tmp_path / "qa.csv"
    csv.write_text("question,answer\nQ,A\n", encoding="utf-8")
    _argv(monkeypatch, tmp_path, "--input-file", str(csv))

    mqr.main()
    assert len(env["registration"]) == 1
    assert env["registration"][0]["provider"] == "gemini"


def test_non_gemini_provider_is_rejected(monkeypatch, tmp_path, env, capsys):
    """`--provider openai` は黙って Gemini で登録せず、argparse が終了コード 2 で拒否する。"""
    csv = tmp_path / "qa.csv"
    csv.write_text("question,answer\nQ,A\n", encoding="utf-8")
    _argv(monkeypatch, tmp_path, "--input-file", str(csv), "--provider", "openai")

    with pytest.raises(SystemExit) as exc:
        mqr.main()
    assert exc.value.code == 2
    assert "--provider" in capsys.readouterr().err
    assert env["registration"] == []
