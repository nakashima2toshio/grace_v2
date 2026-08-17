// 出典リストの解釈。バックエンドは出典を `[社内] …` / `[Web] …` の
// プレフィックス付き文字列で返す（backend/app/core/gates.py::_collect_citations）。
//
// ⚠️ **判定規則をコンポーネント側に散らさない。** 表示文言が「社内」を名乗って
// よいかはこの内訳で決まるため、規則が複数箇所にあると片方だけ直して
// 齟齬が残る（実際にエスカレ時の固定文言がそうなっていた）。

/** 出典 1 件が Web 由来か。 */
export function isWebCitation(text: string): boolean {
  return text.startsWith('[Web]');
}

/** 出典 1 件から表示用のラベル（プレフィックスを除いた本文）を取り出す。 */
export function citationBody(text: string): string {
  return text.replace(/^\[(Web|社内)\]\s*/, '');
}

/** 出典リスト全体の内訳。表示文言が「社内」を名乗ってよいかの判断に使う。 */
export type CitationSourceMix = 'internal' | 'web' | 'mixed' | 'none';

/**
 * 出典リストが社内・Web のどちらに由来するかを判定する。
 *
 * ⚠️ **実測の誤りに対する修正である。**
 * 「明日の東京の天気は？」の実行で、社内 RAG が 0 件で出典 9 件がすべて Web
 * だったにもかかわらず、エスカレ時の固定文言が
 * 「以下は**社内ナレッジ**に基づく参考情報です」と表示された。
 * Web で得た情報を社内ナレッジと偽らないという方針（`grace/tools.py` の
 * 出典ルール 3）は LLM の生成文だけでなく、**アプリ側の固定文言にも適用する**。
 */
export function citationSourceMix(citations: string[]): CitationSourceMix {
  let hasWeb = false;
  let hasInternal = false;
  for (const citation of citations) {
    if (isWebCitation(citation)) hasWeb = true;
    else hasInternal = true;
  }
  if (hasWeb && hasInternal) return 'mixed';
  if (hasWeb) return 'web';
  if (hasInternal) return 'internal';
  return 'none';
}

/**
 * エスカレ時に、生成済みの回答を「参考情報」として添えるときの前置き。
 *
 * 出典の実際の内訳から文言を決める（固定文言にしない）。出典ゼロで
 * ここに来るのは強制エスカレ（エスカレ語検知）のときだけなので、
 * その場合は出典を名乗らない。
 */
export function escalateReferenceNotice(citations: string[]): string {
  const tail = '方針により有人対応へ引き継ぎます。';
  switch (citationSourceMix(citations)) {
    case 'internal':
      return `以下は社内ナレッジに基づく参考情報です。${tail}`;
    case 'web':
      return `以下は Web 検索結果に基づく参考情報です（社内ナレッジには該当がありませんでした）。${tail}`;
    case 'mixed':
      return `以下は社内ナレッジと Web 検索結果に基づく参考情報です。${tail}`;
    case 'none':
      return `以下は参考情報です（出典は取得できていません）。${tail}`;
  }
}

/**
 * 矛盾検知時の注意書き。
 *
 * 内部×Web の相互検証だけでなく Web 内どうしの矛盾でも `contradiction` が
 * 立つため、社内出典が 1 件も無いのに「社内ナレッジと Web 情報で食い違い」と
 * 書いてしまうことがある。社内・Web が揃っているときだけそう名乗る。
 */
export function contradictionNotice(citations: string[]): string {
  return citationSourceMix(citations) === 'mixed'
    ? '⚠️ 注意: 社内ナレッジと Web 情報で食い違いの可能性があります。'
    : '⚠️ 注意: 複数の情報源の間で食い違いの可能性があります。';
}
