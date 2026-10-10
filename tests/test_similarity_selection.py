# tests/test_similarity_selection.py
"""P-04（コサイン類似度の二段構え選抜）の回帰テスト。

背景（`docs/performance_levers.md` §3 P-04）:
一次閾値 0.7 のみだと候補 20 件中 1 件しか残らないことがあり、後段の信頼度評価が
「単一ソースで検証できない」と減点して実質的な回答の信頼度を下げていた
（実測: `コサイン類似度フィルタ: 10 -> 1件` → step 信頼度 0.65 → CONFIRM 発火）。

方針は「現状の高精度ケースを一切変えず、出典不足のケースだけ救う」。
検証すること:
- 一次閾値で十分な件数が取れる場合は**緩和しない**（既存挙動の不変性）
- 0 件・1 件のときだけ緩和し、出典数が増える
- 緩和しても増えないなら一次の結果を返す（無意味な緩和をしない）
- score 降順・limit 件の契約を守る
- 緩和で足すのは**首位スコアから `RELAXED_SCORE_MARGIN` 以内**の候補だけ（首位が強いときは
  低関連の候補を混ぜない。実測 2026-09-29 の「住民票」で、首位 0.80 に 0.62〜0.68 の無関係な
  4 件が混ざっていた）

`agent_tools` はモジュール import 時に Qdrant へ接続しない（遅延）ため、
Qdrant 未起動の CI でも import 可能。
"""
from __future__ import annotations

from agent_tools import (
    COSINE_SIMILARITY_THRESHOLD,
    COSINE_SIMILARITY_THRESHOLD_RELAXED,
    MIN_RESULTS_BEFORE_RELAX,
    RELAXED_SCORE_MARGIN,
    select_by_similarity,
)


def _cands(*scores):
    """スコアだけを持つ検索候補を作る。"""
    return [{"score": s, "payload": {"answer": f"本文{s}"}} for s in scores]


# ---------------------------------------------------------------------------
# 既存挙動の不変性（高精度ケースは緩和しない）
# ---------------------------------------------------------------------------

def test_does_not_relax_when_primary_has_enough():
    """一次閾値で min_results 以上取れるなら緩和しない（0.6 は混入しない）。"""
    results, used = select_by_similarity(_cands(0.95, 0.85, 0.60), limit=3)

    assert used == COSINE_SIMILARITY_THRESHOLD
    assert [r["score"] for r in results] == [0.95, 0.85]


def test_primary_exactly_at_min_results_does_not_relax():
    """ちょうど min_results 件なら緩和しない（境界）。"""
    high = [0.9] * MIN_RESULTS_BEFORE_RELAX
    results, used = select_by_similarity(_cands(*high, 0.55), limit=5)

    assert used == COSINE_SIMILARITY_THRESHOLD
    assert len(results) == MIN_RESULTS_BEFORE_RELAX


def test_threshold_boundary_is_inclusive():
    """閾値ちょうどのスコアは採用する（>= 判定）。"""
    results, used = select_by_similarity(
        _cands(COSINE_SIMILARITY_THRESHOLD, COSINE_SIMILARITY_THRESHOLD), limit=5
    )

    assert used == COSINE_SIMILARITY_THRESHOLD
    assert len(results) == 2


# ---------------------------------------------------------------------------
# 出典不足のケースを救う（P-04 の本題）
# ---------------------------------------------------------------------------

def test_relaxes_when_primary_returns_single_hit():
    """一次で 1 件（首位が閾値すれすれ）→ 首位に近い候補だけ足して出典を増やす。"""
    results, used = select_by_similarity(_cands(0.72, 0.65, 0.55, 0.30), limit=3)

    # 下限 = max(0.5, 0.72 - マージン) = 0.62 → 0.65 は足すが 0.55 は足さない
    assert used < COSINE_SIMILARITY_THRESHOLD
    assert used >= COSINE_SIMILARITY_THRESHOLD_RELAXED
    assert [r["score"] for r in results] == [0.72, 0.65]


def test_strong_top_hit_stands_alone_and_noise_is_not_added():
    """実測ケース: 首位 0.8011 に、0.62〜0.68 の無関係な 4 件（住民票 × 転入届ほか）。

    首位が強いので単独で足りる。緩和しても件数が増えないため一次の結果を返す。
    """
    results, used = select_by_similarity(
        _cands(0.8011, 0.6773, 0.6696, 0.6435, 0.6180), limit=5
    )

    assert [r["score"] for r in results] == [0.8011]
    assert used == COSINE_SIMILARITY_THRESHOLD


def test_relaxes_when_primary_returns_nothing():
    """一次で 0 件 → 首位付近を救う（首位から離れた 0.52 は足さない）。"""
    results, used = select_by_similarity(_cands(0.68, 0.52), limit=3)

    assert [r["score"] for r in results] == [0.68]
    assert COSINE_SIMILARITY_THRESHOLD_RELAXED <= used < COSINE_SIMILARITY_THRESHOLD


def test_relaxed_floor_never_drops_below_the_relaxed_threshold():
    """首位が低くても、下限は緩和閾値（0.5）を割らない。"""
    results, used = select_by_similarity(_cands(0.55, 0.49, 0.30), limit=3)

    assert [r["score"] for r in results] == [0.55]
    assert used == COSINE_SIMILARITY_THRESHOLD_RELAXED


def test_relaxed_results_are_sorted_desc_and_capped_by_limit():
    """緩和時も score 降順・limit 件の契約を守る。"""
    results, used = select_by_similarity(_cands(0.64, 0.72, 0.66, 0.68), limit=2)

    assert used < COSINE_SIMILARITY_THRESHOLD
    assert [r["score"] for r in results] == [0.72, 0.68]


def test_margin_none_keeps_the_legacy_behavior():
    """score_margin=None なら従来どおり緩和閾値だけを下限にする（後方互換）。"""
    results, used = select_by_similarity(
        _cands(0.80, 0.65, 0.55, 0.30), limit=3, score_margin=None
    )

    assert used == COSINE_SIMILARITY_THRESHOLD_RELAXED
    assert [r["score"] for r in results] == [0.80, 0.65, 0.55]


def test_margin_constant_is_sane():
    assert 0.0 < RELAXED_SCORE_MARGIN < COSINE_SIMILARITY_THRESHOLD - COSINE_SIMILARITY_THRESHOLD_RELAXED


# ---------------------------------------------------------------------------
# 無意味な緩和をしない・異常入力
# ---------------------------------------------------------------------------

def test_keeps_primary_when_relaxing_adds_nothing():
    """緩和しても件数が増えないなら一次の閾値・結果を返す。"""
    results, used = select_by_similarity(_cands(0.80, 0.20), limit=3)

    assert used == COSINE_SIMILARITY_THRESHOLD
    assert [r["score"] for r in results] == [0.80]


def test_no_relax_when_relaxed_threshold_not_lower():
    """緩和値が一次以上（設定ミス）なら緩和しない。"""
    results, used = select_by_similarity(
        _cands(0.80, 0.60), limit=3, threshold=0.7, relaxed_threshold=0.7
    )

    assert used == 0.7
    assert [r["score"] for r in results] == [0.80]


def test_empty_candidates_returns_empty():
    """候補なしは空・一次閾値（呼び出し側が NO_RAG_RESULT_LOW_SCORE を返す）。"""
    results, used = select_by_similarity([], limit=3)

    assert results == []
    assert used == COSINE_SIMILARITY_THRESHOLD


def test_missing_score_key_is_treated_as_zero():
    """score が欠けた候補は 0.0 扱いで除外される（KeyError にしない）。"""
    results, used = select_by_similarity(
        [{"payload": {}}, {"score": 0.90, "payload": {}}], limit=3
    )

    assert [r["score"] for r in results] == [0.90]
    assert used == COSINE_SIMILARITY_THRESHOLD


def test_does_not_mutate_input_order():
    """入力リスト自体を並べ替えない（呼び出し側の metrics 計算を壊さない）。"""
    candidates = _cands(0.55, 0.95, 0.60)
    before = [r["score"] for r in candidates]

    select_by_similarity(candidates, limit=3)

    assert [r["score"] for r in candidates] == before
