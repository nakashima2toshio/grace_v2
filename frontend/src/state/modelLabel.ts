// モデル名の表示文字列を組み立てる純関数（ヘッダーのモデルセレクタが使う）。
//
// ## なぜ純関数に切り出すのか
//
// `vite.config.ts` の vitest 設定は `environment: 'node'` かつ
// `include: ['src/**/*.test.ts']` で、**`.test.tsx` は収集されない**。
// つまりコンポーネントのレンダリングテストは書けない。表示の判断（何を出し、
// 何を出さないか）をここへ寄せておけば、`.test.ts` で検証できる（CLAUDE.md §6）。
//
// ⚠️ 既定のモデル名をこのファイルに書かないこと。値は必ず API
// （GET /api/model → config/grace_config.yml の llm.model の解決結果）から来る。
// フロントに既定値を持つと、設定を変えたときに画面と実挙動がずれる。

/** ヘッダーのラベル見出し（エージェントの 3 タブ。`state/headerModel.ts` が使う）。 */
export const MODEL_LABEL_PREFIX = '利用モデル名：';

/**
 * 選択肢 1 つのラベル。モデル名に**入力・出力単価**を添える。
 *
 * 選択肢の単価は最大で 10 倍の開きがある。名前だけを並べると、
 * どれを選ぶと高くつくのかが画面から読み取れない。
 */
export function modelOptionLabel(model: {
  id: string;
  input_price: number;
  output_price: number;
}): string {
  return `${model.id}（入力 $${model.input_price}／出力 $${model.output_price} per 1K）`;
}
