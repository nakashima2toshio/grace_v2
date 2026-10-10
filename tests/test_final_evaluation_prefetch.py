"""回答生成の直後に、最終評価と Groundedness 検証を先行実行し、ステップ確信度の評価と重ねる。

## 何を守っているか

reasoning の後に、次の 3 つの LLM 呼び出しが**順番に**並んでいた
（実測 2026-09-29「住民票の写しの取り方は？」 全体 17 秒のうち約 10 秒）。

    ステップ確信度の評価（haiku）  約 3 秒
    最終評価（自己評価・網羅度）    約 3 秒
    Groundedness 検証               約 4 秒

3 つとも回答本文と出典だけに依存し、互いに独立。先行実行で待ち時間は最長の 1 つ分になる。

⚠️ 重なっていることは**イベントで直接**確かめる（実時間の比較は CI で不安定）。
ステップ確信度の評価が走っている最中に、最終評価と検証が始まっていなければ、
その評価は `Event.wait` がタイムアウトして失敗する（順番待ちの実装だと落ちる）。
LLM・Qdrant・API キーには依存しない。
"""

import copy
import json
import threading
from types import SimpleNamespace

from grace.confidence import GroundednessVerifier
from grace.executor import Executor
from grace.schemas import ExecutionPlan, PlanStep
from grace.tools import ToolResult

QUERY = "明日の東京の天気は？"
WAIT = 5.0  # 秒。重なっていれば一瞬で満たされる。順番待ちなら満たされずタイムアウトする


class _Tool:
    def __init__(self, result):
        self._result = result

    def execute(self, **_kw):
        return self._result


def _registry():
    web = ToolResult(
        success=True,
        output=[{"score": 1.0, "payload": {"answer": "雨時々曇 21℃", "source": "https://ex/1", "title": "t"},
                 "collection": "web_search"}],
        confidence_factors={"result_count": 1, "avg_score": 1.0, "max_score": 1.0, "min_score": 1.0,
                            "score_variance": 0.0, "top_score": 1.0, "score_spread": 0.0},
    )
    rag = ToolResult(
        success=True,
        output=[{"score": 0.9, "payload": {"answer": "x", "source": "a.csv"}, "collection": "c"}],
        confidence_factors={"result_count": 1, "avg_score": 0.9, "max_score": 0.9, "min_score": 0.9,
                            "score_variance": 0.0, "top_score": 0.9, "score_spread": 0.0},
    )
    reasoning = ToolResult(success=True, output="明日は雨時々曇です。",
                           confidence_factors={"source_count": 1})
    tools = {"rag_search": _Tool(rag), "web_search": _Tool(web), "reasoning": _Tool(reasoning)}
    return SimpleNamespace(get=tools.get, list_tools=lambda: list(tools))


def _plan():
    return ExecutionPlan(
        original_query=QUERY, complexity=0.5, estimated_steps=2,
        requires_confirmation=False, success_criteria="x",
        steps=[
            PlanStep(step_id=1, action="rag_search", description="検索", query=QUERY,
                     depends_on=[], expected_output="x", fallback="web_search", timeout_seconds=30),
            PlanStep(step_id=2, action="reasoning", description="回答生成", query=None,
                     depends_on=[1], expected_output="x", timeout_seconds=30),
        ],
    )


def _verdict_json():
    return json.dumps({
        "claims": [{"claim": "明日は雨時々曇である", "verdict": "supported"}],
        "reason": "",
    }, ensure_ascii=False)


class _Harness:
    """Executor を LLM 抜きで組み立て、各呼び出しの開始・順序を記録する。"""

    def __init__(self, monkeypatch, *, prefetch=True, wait=WAIT):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
        monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
        from grace.config import get_config

        cfg = copy.deepcopy(get_config())
        cfg.executor.prefetch_final_evaluation = prefetch
        self.events = []  # 呼び出しの開始・終了の順序
        self.eval_started = threading.Event()
        self.verify_started = threading.Event()
        self.overlap_ok = {"eval": None, "verify": None}
        self.eval_calls = 0
        self.llm_calls = 0

        ex = Executor(config=cfg, tool_registry=_registry(), enable_replan=False)
        ex._memory = None
        self.ex = ex

        # 検証器は本物（キャッシュの挙動を含めて確かめたい）。LLM だけを差し替える。
        verifier = GroundednessVerifier(config=cfg)

        def gen(**_kw):
            self.llm_calls += 1
            self.verify_started.set()
            self.events.append("verify")
            return SimpleNamespace(text=_verdict_json())

        verifier.client = SimpleNamespace(models=SimpleNamespace(generate_content=gen))
        ex.groundedness_verifier = verifier

        def evaluate_final(query, answer, sources):
            self.eval_calls += 1
            self.eval_started.set()
            self.events.append("eval")
            return SimpleNamespace(self_eval_score=0.8, coverage_score=0.7, reason="")

        ex.llm_evaluator.evaluate_final = evaluate_final

        def llm_calculate(factors, **_kw):
            if not factors.is_search_step:  # reasoning ステップの確信度評価
                self.events.append("step2-conf:start")
                # 最終評価と検証が**この評価の最中に**始まっていること
                self.overlap_ok["eval"] = self.eval_started.wait(wait)
                self.overlap_ok["verify"] = self.verify_started.wait(wait)
                self.events.append("step2-conf:end")
            raise RuntimeError("no llm")  # ヒューリスティックへ落とす（LLM に触れない）

        ex.confidence_calculator.llm_calculate = llm_calculate
        ex._evaluate_rag_relevance = lambda **_kw: True

    def run(self):
        return self.ex.execute(_plan())


def test_final_evaluation_and_verification_overlap_with_step_confidence(monkeypatch):
    h = _Harness(monkeypatch)

    result = h.run()

    assert h.overlap_ok["eval"] is True, "最終評価が、ステップ確信度の評価と重なっていない（順番待ち）"
    assert h.overlap_ok["verify"] is True, "Groundedness 検証が、ステップ確信度の評価と重なっていない（順番待ち）"
    assert result.final_answer == "明日は雨時々曇です。"
    assert result.overall_confidence > 0.0


def test_each_llm_call_runs_exactly_once(monkeypatch):
    """先行実行の結果を使い、同じ評価を 2 回走らせない（LLM 代の二重払いを防ぐ）。

    検証は、先行実行の完了を待ってから検証器のキャッシュに当てる。待たずに呼ぶと、
    先行実行が終わる前は**同じ検証をもう一度**走らせてしまう。
    """
    h = _Harness(monkeypatch)

    h.run()

    assert h.eval_calls == 1
    assert h.events.count("verify") == 1


def test_disabled_flag_keeps_the_sequential_order(monkeypatch):
    """設定で無効にすれば従来どおり、確信度の評価が終わってから最終評価・検証へ進む。"""
    h = _Harness(monkeypatch, prefetch=False, wait=0.2)

    result = h.run()

    assert h.overlap_ok == {"eval": False, "verify": False}, "無効なのに先行実行されている"
    assert h.events.index("step2-conf:end") < h.events.index("eval")
    assert h.events.index("step2-conf:end") < h.events.index("verify")
    assert result.overall_confidence > 0.0  # 順番に実行しても結果は同じく計算される


def test_failure_in_prefetched_evaluation_does_not_stop_the_run(monkeypatch):
    """先行実行した最終評価が失敗しても、従来どおり警告だけで全体信頼度は計算される。"""
    h = _Harness(monkeypatch)

    def boom(query, answer, sources):
        h.eval_started.set()
        raise RuntimeError("LLM が落ちた")

    h.ex.llm_evaluator.evaluate_final = boom

    result = h.run()

    assert result.final_answer == "明日は雨時々曇です。"
    assert result.overall_confidence > 0.0


def test_mismatched_inputs_fall_back_to_a_direct_call(monkeypatch):
    """質問・回答・出典が一致しなければ先行結果を使わず、自分で呼ぶ（結果を取り違えない）。"""
    h = _Harness(monkeypatch)
    h.ex._final_prefetch[("eval", "別の質問", "別の回答", ())] = _done_future("STALE")

    got = h.ex._evaluate_final_answer(QUERY, "回答", ["s"])

    assert got != "STALE"
    assert h.eval_calls == 1


def _done_future(value):
    from concurrent.futures import Future

    fut = Future()
    fut.set_result(value)
    return fut
