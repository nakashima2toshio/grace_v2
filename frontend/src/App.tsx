// GRACE のローカル開発用 UI。2 つのエージェントをタブで切り替える。
//
//   Support — 問い合わせ → 回答（/api/support/*）
//   Review  — 文書 → 指摘  （/api/review/*）
//
// ⚠️ タブは**アンマウントで切り替える**（条件レンダリング）。各パネルが自分の
// reducer・SSE 購読・承認状態を持つため、離れた側の EventSource が
// useEffect のクリーンアップで確実に閉じる。
import { useState } from 'react';
import { ReviewPanel } from './components/ReviewPanel';
import { SupportPanel } from './components/SupportPanel';

type Tab = 'support' | 'review';

const TABS: Array<{ id: Tab; label: string; description: string }> = [
  { id: 'support', label: 'GRACE-Support', description: '問い合わせ → 回答' },
  { id: 'review', label: 'GRACE-Review', description: '文書 → 指摘' },
];

export default function App() {
  const [tab, setTab] = useState<Tab>('support');
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

      {tab === 'support' ? <SupportPanel /> : <ReviewPanel />}
    </div>
  );
}
