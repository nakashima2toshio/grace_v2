// チャット入力フォーム: 質問・vertical セレクタ・dry-run トグル・詳細ログトグル。
import { FormEvent, useState } from 'react';
import type { QueryParams, VerticalInfo } from '../types';

const EXAMPLES: Array<{ label: string; query: string; vertical: string | null }> = [
  { label: 'パスワードを忘れました', query: 'パスワードを忘れました', vertical: null },
  { label: 'gov: 住民票の写しの取り方は？', query: '住民票の写しの取り方は？', vertical: 'gov' },
  { label: 'ec: 返品したい', query: '返品したい', vertical: 'ec' },
  { label: 'saas: サービスが落ちています', query: 'サービスが落ちています', vertical: 'saas' },
];

interface Props {
  verticals: VerticalInfo[];
  running: boolean;
  onSubmit: (params: QueryParams) => void;
}

export function QueryForm({ verticals, running, onSubmit }: Props) {
  const [query, setQuery] = useState('');
  const [vertical, setVertical] = useState<string>('');
  const [dryRun, setDryRun] = useState(true);
  const [verbose, setVerbose] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim() || running) return;
    onSubmit({
      query: query.trim(),
      vertical: vertical || null,
      dry_run: dryRun,
      use_web: true,
      do_action: true,
      verbose,
    });
  };

  return (
    <form className="query-form" onSubmit={submit}>
      <div className="query-row">
        <input
          type="text"
          value={query}
          placeholder="問い合わせ内容を入力（例: パスワードを忘れました）"
          onChange={(e) => setQuery(e.target.value)}
          disabled={running}
        />
        <button type="submit" disabled={running || !query.trim()}>
          {running ? '実行中…' : '送信'}
        </button>
      </div>
      <div className="query-options">
        <label>
          業界プロファイル:
          <select
            value={vertical}
            onChange={(e) => setVertical(e.target.value)}
            disabled={running}
          >
            <option value="">（なし）</option>
            {verticals.map((v) => (
              <option key={v.id} value={v.id}>
                {v.id}（{v.name}
                {v.require_identity ? '・本人確認必須' : ''}）
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            disabled={running}
          />
          dry-run（アクションを実行せずログのみ・既定 ON）
        </label>
        <label>
          <input
            type="checkbox"
            checked={verbose}
            onChange={(e) => setVerbose(e.target.checked)}
            disabled={running}
          />
          詳細ログ（-v 相当）
        </label>
      </div>
      <div className="query-examples">
        {EXAMPLES.map((example) => (
          <button
            key={example.label}
            type="button"
            className="example-chip"
            disabled={running}
            onClick={() => {
              setQuery(example.query);
              setVertical(example.vertical ?? '');
            }}
          >
            {example.label}
          </button>
        ))}
      </div>
    </form>
  );
}
