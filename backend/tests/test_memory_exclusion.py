# backend/tests/test_memory_exclusion.py
"""**実行メモリの推測が除外リストを素通りしない**ことを固定するテスト。

## 背景（実測 2026-08-17 11:39 / 11:41）

除外リスト（`qdrant.excluded_collections`）を入れた直後の実行で、除外したはずの
`wikipedia_ja_5per` が検索候補に残り続けていた。

    11:10 天気の実行で誤採用された wikipedia_ja_5per が success=True で記録
      ↓
    [memory] prioritized collection for query: wikipedia_ja_5per
      ↑ 「住民票の写しの取り方は？」でも「明日の東京の天気は？」でも同じ値
      （collection_priors はキーワード重複が無いと全体集計へフォールバックする）
      ↓
    PlanStep.collection にセットされる
      ↓
    RAGSearchTool 側は「明示指定」と区別が付かず protected 扱い → 除外を素通り

11:41 の実測ログでは、除外ログに wikipedia が入らず（cc_news 4 件と fineweb の
5 件だけ）、毎回 Embedding 1 回 + Qdrant 1 回を無駄に消費していた。

**メモリが返すのは「過去の実績からの推測」であって運用者の明示指定ではない。**
除外は運用者が設定した恒久的な意思なので、学習結果より優先する。

## もう 1 つ: docstring と実装が食い違っていた

`_apply_excluded_collections` の docstring は

    「`collection` 引数や業界プロファイルの `allowed_collections` で名指し
      されたコレクションは、除外リストに当たっても落とさない」

と書いていたが、**保護していたのは `collection` 引数だけ**だった。gov プロファイルが
明示的に許可している `wikipedia_ja` は（メモリの保護が無ければ）黙って落ちる。

ここで固定すること:
  1. メモリの推測が除外対象なら使わない（Planner 側で落とす）
  2. 許可リストで名指しされた候補は除外されない（docstring どおり）
  3. 明示指定（collection 引数）は従来どおり保護される
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

from grace.planner import Planner
from grace.tools import RAGSearchTool

EXCLUDED = ["cc_news", "fineweb", "wikipedia", "livedoor", "japanese_text"]


def _planner(best, excluded=None):
    """メモリが `best` を返す Planner を組み立てる（Qdrant/LLM に触れない）。"""
    planner = Planner.__new__(Planner)
    planner.config = SimpleNamespace(
        qdrant=SimpleNamespace(
            excluded_collections=EXCLUDED if excluded is None else excluded,
        ),
        memory=SimpleNamespace(min_count=3, min_score=0.6),
    )
    planner._memory = SimpleNamespace(best_collection=lambda **_kw: best)
    return planner


def _tool(excluded=None):
    tool = RAGSearchTool.__new__(RAGSearchTool)
    tool.config = SimpleNamespace(
        qdrant=SimpleNamespace(
            excluded_collections=EXCLUDED if excluded is None else excluded,
        ),
    )
    return tool


# =============================================================================
# ① メモリの推測に除外を適用する
# =============================================================================

class TestMemoryRespectsExclusion:

    def test_excluded_collection_is_not_prioritized(self, caplog):
        """実測の再現: 誤学習された wikipedia が優先指定されない。"""
        planner = _planner("wikipedia_ja_5per")

        with caplog.at_level(logging.INFO):
            result = planner._prioritized_collection("住民票の写しの取り方は？")

        assert result is None, (
            "除外対象がメモリ経由で復活している（毎回無駄に検索される）"
        )
        assert "除外対象のため使わない" in caplog.text

    def test_allowed_collection_is_still_prioritized(self):
        """除外対象でなければ従来どおり優先する（メモリ機構を殺さない）。"""
        planner = _planner("gov_faq_anthropic")

        assert planner._prioritized_collection("住民票の写しの取り方は？") == "gov_faq_anthropic"

    def test_no_memory_returns_none(self):
        planner = _planner("gov_faq_anthropic")
        planner._memory = None

        assert planner._prioritized_collection("質問") is None

    def test_no_prior_returns_none(self):
        """実績が足りないときは従来どおり None（=全コレクション検索）。"""
        assert _planner(None)._prioritized_collection("質問") is None

    def test_empty_exclusion_setting_is_a_no_op(self):
        assert _planner("wikipedia_ja_5per", excluded=[])._prioritized_collection("q") \
            == "wikipedia_ja_5per"

    def test_partial_match(self):
        """"cc_news" は cc_news_2per_anthropic 等にも一致する。"""
        assert _planner("cc_news_2per_anthropic")._prioritized_collection("q") is None


# =============================================================================
# ② 許可リストで名指しされた候補は保護される
# =============================================================================

class TestAllowedCollectionsAreProtected:
    """⚠️ **`execute()` の実経路で検証する。**

    ヘルパ（`_apply_excluded_collections`）を直接叩くと `protected` を自分で
    渡すことになり、**実際に壊れていた「呼び出し側が protected を組み立てる
    部分」を通らない**。それでは回帰を捕まえられない。
    """

    ALL = ["gov_faq_anthropic", "gov_laws_anthropic", "wikipedia_ja_5per", "cc_news_2per"]

    def _searched(self, monkeypatch, allowed, collection=None):
        """execute() が実際に検索したコレクション名を記録して返す。"""
        tool = RAGSearchTool.__new__(RAGSearchTool)
        tool.config = SimpleNamespace(
            qdrant=SimpleNamespace(
                url="http://localhost:6333",
                collection_name="dummy",
                restrict_to_collection=False,
                allowed_collections=allowed,
                excluded_collections=EXCLUDED,
            ),
            executor=SimpleNamespace(reasoning_min_rag_score=0.64),
        )
        tool.keyword_extractor = None
        called: list[str] = []

        monkeypatch.setattr(
            RAGSearchTool, "_get_all_collections_dynamic", lambda _s: list(self.ALL),
        )
        monkeypatch.setattr(
            "agent_tools.search_rag_knowledge_base_structured",
            lambda _q, col: called.append(col) or [],
        )
        tool.execute(query="住民票の写しの取り方は？", collection=collection)
        return called

    def test_profile_allowed_survives_exclusion(self, monkeypatch):
        """gov プロファイルが明示的に許可する wikipedia_ja は落とさない。

        ⚠️ docstring はそう書いていたのに、実装は `collection` 引数しか
        保護していなかった。
        """
        searched = self._searched(
            monkeypatch, allowed=["gov_faq_anthropic", "gov_laws_anthropic", "wikipedia_ja"],
        )

        assert "wikipedia_ja_5per" in searched, (
            "プロファイルが明示的に許可しているのに除外されている"
        )
        assert "cc_news_2per" not in searched

    def test_generic_corpora_are_dropped_without_a_profile(self, monkeypatch):
        """基本版（許可リストなし）では汎用コーパスを落とす。"""
        searched = self._searched(monkeypatch, allowed=[])

        assert searched == ["gov_faq_anthropic", "gov_laws_anthropic"]

    def test_explicit_collection_argument_is_protected(self, monkeypatch):
        """評価用に汎用コーパスを直接指定できること。"""
        searched = self._searched(
            monkeypatch, allowed=[], collection="wikipedia_ja_5per",
        )

        assert searched[0] == "wikipedia_ja_5per"
