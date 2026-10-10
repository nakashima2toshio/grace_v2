# tests/test_absence_claims.py
"""「情報源に記載がない」型の主張を、支持率・判定率の母数から外すこと。

## 何を守っているか

回答が「参照情報には降水確率が見当たりませんでした」のように答えられない部分を
正直に断ると、その断り文が claim として抽出され、検証器は「情報源に確かに無い」と
確認できるので supported にする。断りが正しいほど支持済みの件数が増え、

- 判定率（M-6 の減衰 `decided / total`）が水増しされる
- 事実に誤りが混ざったときの支持率が水増しされる

実測 2026-09-29（「明日の東京の天気は？」）: supported 7 / neutral 2（total 9）。
うち天気の事実は 2 件で、残り 5 件は「〜は記載がない」型だった。

⚠️ contradicted は外さない。回答が「情報源に無い」と言っているのに載っていた、という
本物の矛盾だから。
"""
from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from grace.confidence import GroundednessVerifier, is_absence_claim
from grace.config import get_config


def _claim(text: str, verdict: str = "supported") -> SimpleNamespace:
    return SimpleNamespace(claim=text, verdict=verdict)


# 実測ログ（2026-09-29 12:26 の `[groundedness] 判定内訳`）そのまま
MEASURED = [
    ("30日（水）の予報は「雨時々曇」である", "supported"),
    ("30日（水）の気温として21℃と19℃が記載されている", "supported"),
    ("21℃と19℃は順序から最高気温・最低気温と考えられる", "neutral"),
    ("情報源[2]には対象地点が東京のどこなのか明示されていない", "supported"),
    ("八丁堀・浅草・市ヶ谷・東京スクエアガーデン・こどもの城のページの抜粋には、30日の具体的な予報内容が含まれていない", "supported"),
    ("meteotrendの抜粋には時間帯ごとの「小雨」「大雨」「+21 °C」という記載がある", "supported"),
    ("meteotrendの抜粋からは、どの日の予報か分からない", "supported"),
    ("明日（30日）の降水確率など詳細は情報源に見当たらない", "supported"),
    ("明日は2026年09月30日・水曜日である", "neutral"),
]


class TestIsAbsenceClaim:
    @pytest.mark.parametrize(
        "text",
        [
            "情報源[2]には対象地点が東京のどこなのか明示されていない",
            "抜粋には30日の具体的な予報内容が含まれていない",
            "明日（30日）の降水確率など詳細は情報源に見当たらない",
            "参照情報には郵送の申請手順が見当たりませんでした",
            "検索結果からは、どの日の予報か分からない",
        ],
    )
    def test_記載なし型は外す(self, text):
        assert is_absence_claim(_claim(text, "supported"))
        assert is_absence_claim(_claim(text, "neutral"))

    def test_contradictedは外さない(self):
        """「情報源に無い」と言っているのに載っていた＝本物の矛盾。"""
        assert not is_absence_claim(_claim("情報源には降水確率が見当たらない", "contradicted"))

    @pytest.mark.parametrize(
        "text",
        [
            "30日（水）の予報は「雨時々曇」である",
            "30日（水）の気温として21℃と19℃が記載されている",  # 「記載」だけでは外さない
            "meteotrendの抜粋には「小雨」「大雨」という記載がある",  # 情報源について肯定的
            "申請書には氏名と住所を記載する必要がある",  # 手続きの事実
            "本人確認ができない場合は郵送で交付できない",  # 「確認」を含む事実
            "住民票の写しは窓口・郵送・コンビニ交付で取得できる",
        ],
    )
    def test_事実の主張は外さない(self, text):
        assert not is_absence_claim(_claim(text, "supported"))

    def test_2語群の両方が必要(self):
        """情報源を指す語だけ・不在の語だけでは外さない。"""
        assert not is_absence_claim(_claim("降水確率は見当たらない", "supported"))
        assert not is_absence_claim(_claim("情報源は3件ある", "supported"))


def _verifier(claims, *, exclude=True):
    cfg = copy.deepcopy(get_config())
    cfg.confidence.groundedness_exclude_absence_claims = exclude
    verifier = GroundednessVerifier(config=cfg)
    payload = json.dumps(
        {"claims": [{"claim": t, "verdict": v} for t, v in claims], "reason": ""},
        ensure_ascii=False,
    )
    verifier.client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **_kw: SimpleNamespace(text=payload)
        )
    )
    return verifier


@pytest.fixture(autouse=True)
def _dummy_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy")
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")


class TestVerifierAggregation:
    def test_実測ケースでは断り文が母数から外れる(self):
        result = _verifier(MEASURED).verify("明日の東京の天気は？", "回答", ["src"])

        # 修正前は supported=7 / total=9（断り 4 件が支持済みに入っていた）
        assert result.supported == 3
        assert result.total == 5
        assert result.contradicted == 0
        # トレース（claims）は全件残す
        assert len(result.claims) == 9

    def test_設定で従来の集計へ戻せる(self):
        result = _verifier(MEASURED, exclude=False).verify("q", "回答", ["src"])

        assert (result.supported, result.total) == (7, 9)

    def test_誤りが混ざったとき断り文で支持率が水増しされない(self):
        claims = [
            ("窓口は平日のみ開いている", "contradicted"),
            ("手数料は300円である", "supported"),
            ("情報源には受付時間が見当たらない", "supported"),
            ("情報源には郵送の手順が見当たらない", "supported"),
            ("参照情報にはコンビニ交付の詳細が見当たらない", "supported"),
        ]
        result = _verifier(claims).verify("q", "回答", ["src"])

        assert result.support_rate == 0.5  # 1 / (1 + 1)。断りを数えると 4/5 = 0.8

    def test_contradictedの断り文は外さず矛盾として残る(self):
        claims = [
            ("手数料は300円である", "supported"),
            ("情報源には受付時間が見当たらない", "contradicted"),
        ]
        result = _verifier(claims).verify("q", "回答", ["src"])

        assert result.has_contradiction is True
        assert result.contradicted == 1

    def test_全部が断り文なら除外せず従来どおり集計する(self):
        """除外すると検証対象が 0 になり「未検証」へ倒れてしまう。"""
        claims = [
            ("情報源には降水確率が見当たらない", "supported"),
            ("抜粋には地点名が含まれていない", "supported"),
        ]
        result = _verifier(claims).verify("q", "回答", ["src"])

        assert result.verified is True
        assert result.total == 2
