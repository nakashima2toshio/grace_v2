// GRACE のローカル開発用 UI。4 つのメニューをタブで切り替える。
//
//   基本版         — 問い合わせ → 回答（業界特化なし・/api/support/*）
//   GRACE-Support  — 問い合わせ → 回答（業界プロファイル適用・/api/support/*）
//   GRACE-Review   — 文書 → 指摘（ルールセット適用・/api/review/*）
//   データ管理     — チャンキング → Qdrant 登録 → コレクション管理（/api/data/* ほか）
//
// 前 3 つは「エージェントを使う」側、最後の 1 つは「データを準備する」側で、
// モードが異なる。前者の並びは「業界特化を足していく順」で、基本版が素の
// パイプライン、Support は VerticalProfile、Review は RuleSet を差し替えたもの。
// この 2 つの業界定義はほぼ同型（collections / *_keywords / action_map /
// notify_th / confirm_th / prompt_addendum を共有）である。
//
// ⚠️ タブは**アンマウントで切り替える**（条件レンダリング）。各パネルが自分の
// reducer・SSE 購読・承認状態を持つため、離れた側の EventSource が
// useEffect のクリーンアップで確実に閉じる。
import { useState } from 'react';
import { DataPanel } from './components/DataPanel';
import { ReviewPanel } from './components/ReviewPanel';
import { SupportPanel } from './components/SupportPanel';

type Tab = 'basic' | 'support' | 'review' | 'data';

const TABS: Array<{ id: Tab; label: string; description: string }> = [
  { id: 'basic', label: '基本版', description: '問い合わせ → 回答（業界特化なし）' },
  { id: 'support', label: 'GRACE-Support', description: '問い合わせ → 回答（業界特化）' },
  { id: 'review', label: 'GRACE-Review', description: '文書 → 指摘（業界特化）' },
  { id: 'data', label: 'データ管理', description: 'チャンク化 → 登録 → コレクション管理' },
];

export default function App() {
  const [tab, setTab] = useState<Tab>('basic');
  const active = TABS.find((t) => t.id === tab) ?? TABS[0];

  return (
    <div className="app">
      <header>
        <h1>{active.label}</h1>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={t.id === tab}
              className={`tab${t.id === tab ? ' active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
              <span className="tab-sub">{t.description}</span>
            </button>
          ))}
        </nav>
      </header>

      {tab === 'data' ? (
        <DataPanel />
      ) : tab === 'review' ? (
        <ReviewPanel />
      ) : (
        // 基本版と Support は同一パイプライン。variant で業界特化の有無だけを切り替える。
        <SupportPanel key={tab} variant={tab === 'basic' ? 'basic' : 'vertical'} />
      )}
    </div>
  );
}
