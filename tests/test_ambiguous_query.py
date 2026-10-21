"""曖昧クエリ判定（`grace.planner.is_ambiguous_query`）を守るテスト。

## なぜ必要か（実測 2026-10-22・Mac の ./run_dev.sh）

基本版タブに次の 3 行を 1 つの問い合わせとして送ると、2 行目の「その件」だけを見て
曖昧と判定され、計画が ask_user（聞き返し）1 ステップになった::

    Jed York CEOが新しいGMとコーチを探す背景には、どのような経緯がありますか？
    その件の経緯を詳しく教えて
    最新ニュースを検索して、49ersの新GMとヘッドコーチの人事を教えて

1 行目に対象（Jed York・49ers）が書かれているのに、社内検索（RAG）が一度も呼ばれず、
`cc_news_2per_anthropic` にある情報が使われないまま ⑤ Web → escalate になった。

「その件」は**前に書いた対象を指す**ので、それより前に具体的な手がかり
（英数字・3 文字以上のカタカナ語）があれば曖昧ではない。

LLM・Qdrant・API キーには依存しない。
"""

import pytest

from grace.planner import is_ambiguous_query

SCREEN_INPUT = (
    "Jed York CEOが新しいGMとコーチを探す背景には、どのような経緯がありますか？\n"
    "その件の経緯を詳しく教えて\n"
    "最新ニュースを検索して、49ersの新GMとヘッドコーチの人事を教えて"
)


class TestReferentResolvedEarlier:
    def test_screen_input_with_subject_on_first_line_is_not_ambiguous(self):
        assert is_ambiguous_query(SCREEN_INPUT) is False

    def test_subject_before_referent_in_one_line_is_not_ambiguous(self):
        assert is_ambiguous_query("49ersのGM人事について。その件の経緯は？") is False


class TestStillAmbiguous:
    """単独の「その件」は従来どおり曖昧（ask_user で聞き返す）。"""

    @pytest.mark.parametrize("query", [
        "その件の経緯を詳しく教えて",
        "あの件について教えて",
        "例の話はどうなりましたか",
    ])
    def test_referent_alone_is_ambiguous(self, query):
        assert is_ambiguous_query(query) is True

    def test_clue_only_after_referent_is_still_ambiguous(self):
        """手がかりが「あの件」より後ろにあっても、何の件かは決まらない。"""
        assert is_ambiguous_query("あの件のメールを確認して") is True

    def test_short_demonstrative_without_clue_is_ambiguous(self):
        assert is_ambiguous_query("それはどうなった？") is True

    def test_empty_is_ambiguous(self):
        assert is_ambiguous_query("") is True


class TestConcreteQueries:
    @pytest.mark.parametrize("query", [
        "Jed York CEOが新しいGMとコーチを探す背景には、どのような経緯がありますか？",
        "最新ニュースを検索して、49ersの新GMとヘッドコーチの人事を教えて",
        "住民票の写しの取り方は？",
    ])
    def test_concrete_query_is_not_ambiguous(self, query):
        assert is_ambiguous_query(query) is False
