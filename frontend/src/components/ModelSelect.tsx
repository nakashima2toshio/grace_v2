// 3タブ共通の LLM モデルセレクタ。QueryForm（基本版・GRACE-Support）・
// ReviewForm（GRACE-Review）・DataJobPanel（データ管理）から使う（重複防止）。
//
// 選択肢は GET /api/models（config.py::get_selectable_models()）から取得した
// ものだけ。旧既定（claude-sonnet-4-6）や日付指定エイリアスは含まれない。
//
// 未選択（空文字）は「サーバーの既定値を使う」を意味し、buildQueryParams /
// buildChunkingParams / buildQaParams / ReviewForm の送信処理でそれぞれ
// null 化またはキーごと省略される。
//
// ⚠️ `defaultModel` を渡すと未選択の項目に**実際の既定モデル名**が出る。
// 何も渡さないと「（既定値）」としか出ず、画面はどのモデルで走るかを
// 示さないままになる。
//
// ⚠️ Embedding はここに出ない。Embedding は Gemini（gemini-embedding-001
// 3072 次元）固定で、変えると既存 Qdrant コレクションと次元が合わない。
import { defaultOptionLabel, modelOptionLabel } from '../state/modelLabel';
import type { ModelChoice } from '../types';

interface Props {
  models: ModelChoice[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  /**
   * サーバーが既定として使うモデル名（`GET /api/model` の `model`）。
   * 渡すと未選択の項目が「（既定値: <名前>）」になり、**何で走るかが見える**。
   * 未取得なら空文字（「（既定値）」と出る）。
   */
  defaultModel?: string;
}

export function ModelSelect({ models, value, onChange, disabled, defaultModel }: Props) {
  return (
    <label>
      モデル
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        <option value="">{defaultOptionLabel(defaultModel ?? '')}</option>
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {modelOptionLabel(m)}
          </option>
        ))}
      </select>
    </label>
  );
}
