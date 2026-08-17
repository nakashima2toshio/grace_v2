# backend/tests/test_source_attribution.py
"""回答が**出典の種別と対応付けを偽らない**ことを固定するテスト。

## 背景（grace_v2_local で実測、本リポジトリにも同じコードが残っていた）

回答規則が出典の種別を問わず「社内ナレッジ（出典ファイル名）によると...」を
指示していたため、LLM は指示どおり Web の内容にもこの形式を当てはめた:

    Yahoo!天気によると、…確認できる情報源があります（社内ナレッジ（web_search））。

Yahoo!天気は社内ナレッジではない。**外部 Web の内容を社内の裏付けとして提示する**
のは、根拠の信頼性を売りにするこのシステムで最も避けたい壊れ方であり、
**どのゲートでも検出できない** — 述べている内容自体は情報源に忠実なので
groundedness は下がらず、出典もあり、本文もあるためである。

同じ根の誤りが 2 つ続いていた:

1. **Web 情報源どうしの取り違え** — 情報源 7（Yahoo）の文章に情報源 8
   （tenki.jp）の URL を付けた。実在しないドメイン（webath.co.jp）を書いた例も
   ある。規則が「サイト名または URL」を許していたため、記憶から補う余地が
   残っていた。
2. **内部の通し番号が回答に出る** — 「別の情報源（情報源7）で…」。番号は
   プロンプト内部のもので、読む人には何のことか分からない。

## ⚠️ これは規則の追加であって保証ではない

規則を足したからといってモデルが従うとは限らない。ここが固定しているのは
**規則がプロンプトに載っていること**だけで、出力が正しくなることではない。

ここで固定すること:
  1. 情報源の見出しに種別（【社内】/【Web】）が付くこと
  2. 種別の判定が collection と URL 形式の 2 段構えであること
  3. 種別ごとに異なる出典形式を指示していること
  4. 出典は「出典:」行から書き写す指示であること（サイト名の逃げ道が無い）
  5. 内部番号を本文で使わない指示があること
  6. UI の固定文言が出典の実態に合わせて変わること

⚠️ LLM には接続しない（プロンプト構築だけを見る）。
"""
from __future__ import annotations

from grace.tools import ReasoningTool

QUERY = "明日の東京の天気は？"

INTERNAL_SOURCE = {
    "collection": "customer_support_faq",
    "score": 0.81,
    "payload": {
        "question": "パスワードを忘れました",
        "answer": "マイページから再設定できます。",
        "source": "faq_customer_support.csv",
    },
}
WEB_SOURCE = {
    "collection": "web_search",
    "score": 0.72,
    "payload": {
        "content": "東京の今日・明日の天気、気温、降水確率をお伝えします。",
        "source": "https://weather.yahoo.co.jp/weather/jp/13/",
    },
}
# collection が落ちた経路でも URL 形式で Web と分かること
WEB_SOURCE_NO_COLLECTION = {
    "score": 0.70,
    "payload": {
        "content": "明日までの天気予報を確認できます。",
        "source": "https://tenki.jp/forecast/3/16/",
    },
}


def _prompt(sources):
    return ReasoningTool()._build_prompt(QUERY, None, sources)


# =============================================================================
# ① 種別の判定
# =============================================================================

class TestSourceOrigin:

    def test_web_search_collection_is_web(self):
        assert ReasoningTool._source_origin(WEB_SOURCE) == "Web"

    def test_url_source_is_web_even_without_collection(self):
        """collection が落ちる経路があるので URL 形式でも判定する。"""
        assert ReasoningTool._source_origin(WEB_SOURCE_NO_COLLECTION) == "Web"

    def test_internal_collection_is_internal(self):
        assert ReasoningTool._source_origin(INTERNAL_SOURCE) == "社内"

    def test_http_url_is_web(self):
        source = {"payload": {"source": "http://example.com/a"}}
        assert ReasoningTool._source_origin(source) == "Web"

    def test_missing_payload_defaults_to_internal(self):
        """判定材料が無いときは社内扱い（従来の見え方を変えない）。"""
        assert ReasoningTool._source_origin({}) == "社内"


# =============================================================================
# ② 見出しに種別が載る
# =============================================================================

class TestOriginAppearsInPrompt:

    def test_each_source_heading_carries_its_kind(self):
        prompt = _prompt([INTERNAL_SOURCE, WEB_SOURCE])

        assert "情報源 1 【社内】" in prompt
        assert "情報源 2 【Web】" in prompt

    def test_web_source_is_not_labelled_internal(self):
        """ここが壊れると Web が社内ナレッジとして提示される。"""
        prompt = _prompt([WEB_SOURCE])

        assert "情報源 1 【Web】" in prompt
        assert "情報源 1 【社内】" not in prompt

    def test_score_and_collection_are_kept(self):
        """既存の情報を落としていないこと。"""
        prompt = _prompt([INTERNAL_SOURCE])

        assert "信頼度: 0.81" in prompt
        assert "コレクション: customer_support_faq" in prompt
        assert "出典: faq_customer_support.csv" in prompt


# =============================================================================
# ③ 回答規則
# =============================================================================

class TestAnswerRules:

    def test_attribution_branches_by_kind(self):
        prompt = _prompt([WEB_SOURCE])

        assert "【社内】の情報源 → 「社内ナレッジ（出典ファイル名）によると...」" in prompt
        assert "【Web】の情報源 → 「Web 検索結果（URL）によると...」" in prompt

    def test_faking_the_kind_is_forbidden(self):
        prompt = _prompt([WEB_SOURCE])

        assert "Web で得た情報を「社内ナレッジ」と書いてはいけません" in prompt

    def test_unconditional_internal_attribution_is_gone(self):
        """旧規則が残っていると、それだけで Web にも社内形式が適用される。"""
        prompt = _prompt([WEB_SOURCE])

        assert "3. **出典の明示**: 回答の根拠となった情報がある場合、"\
               "「社内ナレッジ（出典ファイル名）によると...」" not in prompt

    def test_source_line_must_be_transcribed(self):
        """「サイト名」を許すと記憶から補う余地が残る（実在しないドメインの実測あり）。"""
        prompt = _prompt([WEB_SOURCE])

        assert "「出典:」行を**そのまま省略せずに**書き写して" in prompt
        assert "サイト名または URL" not in prompt, (
            "サイト名を許す逃げ道が残っている"
        )

    def test_domain_completion_from_memory_is_forbidden(self):
        prompt = _prompt([WEB_SOURCE])

        assert "サイト名やドメインを記憶から補わないでください" in prompt
        assert "捏造にあたります" in prompt

    def test_one_statement_maps_to_one_source(self):
        prompt = _prompt([WEB_SOURCE, WEB_SOURCE_NO_COLLECTION])

        assert "情報源を 1 つだけ対応させ" in prompt
        assert "複数の情報源の内容を 1 つの箇条書きに混ぜないでください" in prompt

    def test_internal_numbering_must_not_appear_in_the_answer(self):
        prompt = _prompt([WEB_SOURCE])

        assert "情報源番号を書かない" in prompt
        assert "本文で参照しないでください" in prompt

    def test_existing_rules_survive(self):
        """規則の入れ替えで既存の歯止めを落としていないこと。"""
        prompt = _prompt([INTERNAL_SOURCE])

        assert "正確性と誠実さ" in prompt
        assert "捏造禁止" in prompt
        assert "丁寧な日本語" in prompt

    def test_rule_numbers_are_sequential(self):
        prompt = _prompt([INTERNAL_SOURCE])

        for n in range(1, 8):
            assert f"\n{n}. **" in prompt, f"規則 {n} が欠番"
