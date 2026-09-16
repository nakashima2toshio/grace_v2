// モデル名の表示文字列を組み立てる純関数。
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
import type { ModelInfo } from '../types';

/** ヘッダーのラベル見出し。 */
export const MODEL_LABEL_PREFIX = '利用モデル名：';

/**
 * ヘッダーに出すモデル名を返す。**出せない情報は出さない**（null を返す）。
 *
 * - 取得前・取得失敗（`info === null`）→ null（ヘッダーに何も出さない）
 * - `model` が空文字 → null（「利用モデル名：」だけが出るのを防ぐ）
 * - `heavy_model` が設定されていて `model` と異なる → 併記する。
 *   論理層（計画生成・推論・根拠検証）だけ別モデルへ寄せている状態を隠すと、
 *   ヘッダーが実際の挙動について嘘をつくことになるため。
 */
export function formatModelLabel(info: ModelInfo | null): string | null {
  if (info === null) return null;

  const model = info.model.trim();
  if (!model) return null;

  const heavy = info.heavy_model.trim();
  if (heavy && heavy !== model) {
    return `${model}（論理層: ${heavy}）`;
  }
  return model;
}

/** `ModelSelect` の「未選択」項目のラベル（既定値が不明なときの文言）。 */
export const DEFAULT_OPTION_FALLBACK = '（既定値）';

/**
 * 「未選択 = サーバーの既定値」の選択肢に出す文字列を返す。
 *
 * 既定値が分かっているなら**名前まで出す**。`（既定値）` のままだと、画面は
 * どのモデルで走るかを一切示さないことになる。
 *
 * @param defaultModel `GET /api/model` の `model`。未取得・失敗時は空文字
 */
export function defaultOptionLabel(defaultModel: string): string {
  const name = defaultModel.trim();
  return name ? `（既定値: ${name}）` : DEFAULT_OPTION_FALLBACK;
}

/**
 * 選択肢 1 つのラベル。モデル名に**入力単価**を添える。
 *
 * 単価は 3 つで 5 倍の開きがある（$0.001 / $0.002 / $0.005 per 1K tokens）。
 * 名前だけを並べると、どれを選ぶと高くつくのかが画面から読み取れない。
 */
export function modelOptionLabel(model: {
  id: string;
  input_price: number;
  output_price: number;
}): string {
  return `${model.id}（入力 $${model.input_price}／出力 $${model.output_price} per 1K）`;
}
