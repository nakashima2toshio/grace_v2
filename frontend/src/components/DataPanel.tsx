// データ管理タブのルート。パイプラインの流れ順にサブタブを並べる。
//
//   ① チャンキング → ② Qdrant 登録 → ③ コレクション管理
//
// エージェント 3 タブ（基本版 / Support / Review）が「エージェントを使う」側なのに対し、
// こちらは「データを準備する」側で、モードが違うので入れ子のタブにしてある。
//
// ⚠️ `key={sub}` は必須。無いと React が同じ位置のコンポーネントを再利用し、
// 前のサブタブの reducer 状態と SSE 購読が残る（App.tsx のタブ切替と同じ理由）。
import { useState } from 'react';

import { CollectionPanel } from './CollectionPanel';
import { DataJobPanel } from './DataJobPanel';

type SubTab = 'chunking' | 'register' | 'collections';

const SUB_TABS: Array<{ id: SubTab; label: string; description: string }> = [
  {
    id: 'chunking',
    label: '① チャンキング',
    description: 'CSV / テキスト → セマンティックチャンク CSV',
  },
  {
    id: 'register',
    label: '② Qdrant 登録',
    description: 'Q/A CSV → Qdrant コレクション（Embedding 生成つき）',
  },
  {
    id: 'collections',
    label: '③ コレクション管理',
    description: '一覧・プレビュー・削除（削除は承認が必要）',
  },
];

export function DataPanel() {
  const [sub, setSub] = useState<SubTab>('chunking');
  const active = SUB_TABS.find((t) => t.id === sub) ?? SUB_TABS[0];

  return (
    <>
      <nav className="sub-tabs" role="tablist" aria-label="データ準備の工程">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={sub === tab.id}
            className={sub === tab.id ? 'active' : ''}
            onClick={() => setSub(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <p className="tab-description">{active.description}</p>

      {sub === 'collections' ? (
        <CollectionPanel key={sub} />
      ) : (
        <DataJobPanel key={sub} variant={sub} />
      )}
    </>
  );
}
