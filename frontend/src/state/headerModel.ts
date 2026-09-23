// ヘッダーのモデルセレクタ（基本版 / GRACE-Support / GRACE-Review）の判断を
// まとめた純関数。
//
// ## なぜヘッダーにあるのか
//
// モデルは「そのタブで何を使って走るか」という画面全体の設定なので、
// タイトル横（`利用モデル名：`）で選ぶ。以前は各フォームの中にセレクタがあり、
// ヘッダーは既定値を表示するだけだったため、同じ情報が 2 箇所に出ていた。
//
// ## 未選択（空文字）の意味
//
// 空文字 = 「サーバーの既定値を使う」。送信時は `buildQueryParams` / ReviewForm が
// null へ倒し、サーバーが `config/grace_config.yml` の `llm.model` で走る。
// ⚠️ 既定のモデル名をフロントに持たないこと（値は GET /api/model から来る）。
//
// ## 選択はタブごと
//
// 基本版と GRACE-Support は同じパイプラインだが**別のタブ**なので、片方で
// 選んだモデルがもう片方へ漏れないよう記憶を分ける（formMemory と同じ方針）。
// 値は `App` の state に持つ。`App` はアンマウントされないので、
// タブを切り替えても選択は残る。
import type { ModelChoice } from '../types';
import { modelOptionLabel } from './modelLabel';

/** ヘッダーでモデルを選べるタブ。データ管理タブは工程ごとにモデルが違うので対象外。 */
export type ModelTab = 'basic' | 'support' | 'review';

/** タブごとの選択。空文字 = 未選択（サーバーの既定値）。 */
export type HeaderModels = Record<ModelTab, string>;

export const INITIAL_HEADER_MODELS: HeaderModels = { basic: '', support: '', review: '' };

/** そのタブがヘッダーでモデルを選ぶタブか。 */
export function isModelTab(tab: string): tab is ModelTab {
  return tab === 'basic' || tab === 'support' || tab === 'review';
}

/**
 * セレクタに表示する値。未選択ならサーバーの既定モデル名を出す。
 *
 * ⚠️ 未選択のまま空欄を表示しない。「何で走るか」が画面から消えるため。
 */
export function headerSelectValue(selected: string, defaultModel: string): string {
  return selected.trim() || defaultModel.trim();
}

export interface HeaderModelOption {
  id: string;
  label: string;
}

/**
 * セレクタの選択肢。GET /api/models の一覧に単価を添えたもの。
 *
 * 既定モデルが一覧に無い（設定ファイルで選択肢外のモデルを指している）場合は
 * 先頭に足す。足さないと `<select>` の表示が別の選択肢へずれ、
 * 実際に走るモデルと画面が食い違う。
 */
export function headerModelOptions(
  models: ModelChoice[],
  defaultModel: string,
): HeaderModelOption[] {
  const options = models.map((m) => ({ id: m.id, label: modelOptionLabel(m) }));
  const name = defaultModel.trim();
  if (name && !models.some((m) => m.id === name)) {
    options.unshift({ id: name, label: name });
  }
  return options;
}

/**
 * 論理層だけ別モデルへ寄せている（`llm.heavy_model`）ときの注記。
 * 無ければ null。ヘッダーがセレクタになっても、この事実は隠さない。
 */
export function heavyModelNote(model: string, heavyModel: string): string | null {
  const heavy = heavyModel.trim();
  if (!heavy || heavy === model.trim()) return null;
  return `（論理層: ${heavy}）`;
}
