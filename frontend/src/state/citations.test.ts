// 出典の内訳から表示文言を決めるロジックのテスト。
//
// 背景（実測）: 社内 RAG が 0 件で出典がすべて Web だったにもかかわらず、
// エスカレ時の前置きが「以下は社内ナレッジに基づく参考情報です」という
// 固定文言だった。Web で得た情報を社内ナレッジと偽らない方針
// （grace/tools.py の出典ルール 3）は、LLM の生成文だけでなく
// アプリ側の固定文言にも適用する。
import { describe, expect, it } from 'vitest';

import {
  citationBody,
  citationSourceMix,
  contradictionNotice,
  escalateReferenceNotice,
  isWebCitation,
} from './citations';

const WEB = '[Web] Yahoo!天気 https://weather.yahoo.co.jp/weather/jp/13/';
const WEB2 = '[Web] tenki.jp https://tenki.jp/forecast/3/16/';
const INTERNAL = '[社内] faq_customer_support.csv';

describe('isWebCitation / citationBody', () => {
  it('プレフィックスで種別を判定する', () => {
    expect(isWebCitation(WEB)).toBe(true);
    expect(isWebCitation(INTERNAL)).toBe(false);
  });

  it('表示用にプレフィックスを落とす', () => {
    expect(citationBody(INTERNAL)).toBe('faq_customer_support.csv');
    expect(citationBody(WEB)).toBe('Yahoo!天気 https://weather.yahoo.co.jp/weather/jp/13/');
  });
});

describe('citationSourceMix', () => {
  it('すべて Web なら web', () => {
    expect(citationSourceMix([WEB, WEB2])).toBe('web');
  });

  it('すべて社内なら internal', () => {
    expect(citationSourceMix([INTERNAL])).toBe('internal');
  });

  it('混在なら mixed', () => {
    expect(citationSourceMix([INTERNAL, WEB])).toBe('mixed');
  });

  it('空なら none', () => {
    expect(citationSourceMix([])).toBe('none');
  });
});

describe('escalateReferenceNotice', () => {
  it('出典が Web だけのとき「社内ナレッジに基づく」と言わない', () => {
    const notice = escalateReferenceNotice([WEB, WEB2]);

    expect(notice).toContain('Web 検索結果に基づく');
    expect(notice).toContain('社内ナレッジには該当がありませんでした');
    expect(notice).not.toMatch(/^以下は社内ナレッジに基づく/);
  });

  it('出典が社内だけのときは従来どおり', () => {
    expect(escalateReferenceNotice([INTERNAL])).toContain('社内ナレッジに基づく参考情報');
  });

  it('混在のときは両方を名乗る', () => {
    expect(escalateReferenceNotice([INTERNAL, WEB])).toContain(
      '社内ナレッジと Web 検索結果に基づく',
    );
  });

  it('出典ゼロ（強制エスカレ）のときは出典を名乗らない', () => {
    const notice = escalateReferenceNotice([]);

    expect(notice).toContain('出典は取得できていません');
    expect(notice).not.toContain('社内ナレッジに基づく');
  });

  it('どの分岐でも引き継ぎ文が付く', () => {
    for (const citations of [[INTERNAL], [WEB], [INTERNAL, WEB], []]) {
      expect(escalateReferenceNotice(citations)).toContain('有人対応へ引き継ぎます');
    }
  });
});

describe('contradictionNotice', () => {
  it('社内と Web が揃っているときだけ「社内ナレッジと Web 情報」と言う', () => {
    expect(contradictionNotice([INTERNAL, WEB])).toContain('社内ナレッジと Web 情報');
  });

  it('Web どうしの矛盾では社内を名乗らない', () => {
    const notice = contradictionNotice([WEB, WEB2]);

    expect(notice).toContain('複数の情報源の間で');
    expect(notice).not.toContain('社内ナレッジと Web 情報');
  });
});
