"""`scripts/measure_rag_scores.py` の集計（純関数）のテスト。API・Qdrant に依存しない。

実データでの計測は Mac で流す（スクリプトの docstring）。ここでは「どの帯に入ったら
executor がどう振る舞うか」の判定と、範囲内・範囲外の集計が正しいことを守る。
"""

import pytest

from scripts.measure_rag_scores import analyze, build_queries, load_queries, zone

ADOPT, SUFFICIENT = 0.64, 0.64


@pytest.mark.parametrize("score, expected", [
    (0.50, "rejected"),      # 採用されない → Web へ
    (0.6399, "rejected"),
    (0.64, "relevance"),     # 採用される → LLM の適合性チェックが Web の要否を決める
    (0.665, "relevance"),    # 範囲内の質問の実測最小（2026-10-04 までの 0.7 では forced_web だった）
    (0.90, "relevance"),
])
def test_zone_with_aligned_thresholds(score, expected):
    assert zone(score, ADOPT, SUFFICIENT) == expected


def test_zone_reports_forced_web_when_sufficient_is_above_adoption():
    """しきい値が食い違うと、採用したのに無条件で Web も検索する帯ができる（旧 0.7）。"""
    assert zone(0.665, 0.64, 0.7) == "forced_web"


def test_build_queries_uses_other_screen_examples_as_out_of_scope():
    rows = build_queries({"gov": "住民票?", "ec": "返品?"}, ["gov", "ec"])

    assert ("gov", "in", "住民票?") in rows
    assert ("gov", "out", "返品?") in rows     # 他の業界の例文は範囲外
    assert ("ec", "out", "住民票?") in rows
    assert not [r for r in rows if r[1] not in ("in", "out")]


def test_analyze_counts_behaviour_under_current_thresholds():
    rows = [
        {"vertical": "gov", "label": "in", "top": 0.80},
        {"vertical": "gov", "label": "in", "top": 0.665},
        {"vertical": "gov", "label": "in", "top": 0.60},    # 範囲内なのに採用されない
        {"vertical": "gov", "label": "out", "top": 0.55},
        {"vertical": "gov", "label": "out", "top": 0.66},   # 範囲外なのに採用される
    ]

    gov = analyze(rows, adopt=0.64, sufficient=0.7)["gov"]

    assert gov["in"] == {"n": 3, "min": 0.6, "median": 0.665, "max": 0.8}
    assert gov["out"] == {"n": 2, "max": 0.66}
    assert gov["in_rejected"] == 1
    assert gov["in_forced_web"] == 1          # 0.665（0.64 ≤ s < 0.7）
    assert gov["out_adopted"] == 1
    assert gov["margin"] == pytest.approx(-0.06)
    assert gov["midpoint"] is None            # 範囲内の最小 < 範囲外の最大 → 1 本のしきい値では分けられない


def test_analyze_midpoint_when_separable():
    rows = [{"vertical": "ec", "label": "in", "top": 0.665},
            {"vertical": "ec", "label": "out", "top": 0.619}]

    ec = analyze(rows, adopt=0.64, sufficient=0.64)["ec"]

    assert ec["margin"] == pytest.approx(0.046)
    assert ec["midpoint"] == pytest.approx(0.642)
    assert analyze(rows, 0.64, 0.64)["(all)"]["in"]["n"] == 1


def test_load_queries_rejects_unknown_label(tmp_path):
    path = tmp_path / "q.csv"
    path.write_text("vertical,label,query\ngov,maybe,何か\n", encoding="utf-8")

    with pytest.raises(ValueError, match="in / out"):
        load_queries(path)
