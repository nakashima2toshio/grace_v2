// 回答カード: decision バッジ（answer=緑 / escalate=赤）、回答本文、出典リスト
// （[社内] と [Web] を区別表示）、groundedness スコア、エスカレ理由、アクション結果。
import type { SupportResult } from '../types';
import { Markdown } from './Markdown';

function escalateReason(result: SupportResult): string {
  if (result.forced_escalate) {
    return `エスカレ語を検知（意図分類: ${result.intent ?? '不明'}）による強制エスカレ`;
  }
  if (result.no_info_detected) {
    return '「情報なし回答」を検知（④\' ゲート）';
  }
  return '出典・支持率がしきい値未達（回答ゲート）';
}

function Citation({ text }: { text: string }) {
  const isWeb = text.startsWith('[Web]');
  return (
    <li className={isWeb ? 'citation-web' : 'citation-internal'}>
      <span className="citation-label">{isWeb ? 'Web' : '社内'}</span>
      {text.replace(/^\[(Web|社内)\]\s*/, '')}
    </li>
  );
}

export function AnswerCard({ result }: { result: SupportResult }) {
  const isAnswer = result.decision === 'answer';
  return (
    <section className={`answer-card ${isAnswer ? 'answer' : 'escalate'}`}>
      <div className="answer-header">
        <span className={`decision-badge ${result.decision}`}>
          {isAnswer ? 'answer（回答）' : 'escalate（有人対応へ）'}
        </span>
        {result.vertical && <span className="badge">vertical: {result.vertical}</span>}
        {result.used_web && <span className="badge">Web 使用</span>}
        {result.web_reused && <span className="badge">Web 再利用</span>}
      </div>

      {isAnswer ? (
        <>
          {result.answer ? (
            <Markdown source={result.answer} />
          ) : (
            <p className="answer-text">（回答なし）</p>
          )}
          {result.warning && (
            <p className="notice">
              ⚠️ 注意: この回答は出典による裏付けが十分ではありません。内容をご確認ください。
            </p>
          )}
          {result.used_web && result.contradiction && (
            <p className="notice">
              ⚠️ 注意: 社内ナレッジと Web 情報で食い違いの可能性があります。
            </p>
          )}
          {result.citations.length > 0 && (
            <div className="citations">
              <h3>出典</h3>
              <ul>
                {result.citations.map((citation) => (
                  <Citation key={citation} text={citation} />
                ))}
              </ul>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="answer-text">
            社内ナレッジにも Web 検索にも十分な根拠が見つかりませんでした。
            <br />→ 有人対応へエスカレーションします。
          </p>
          <p className="notice">理由: {escalateReason(result)}</p>
        </>
      )}

      {result.action && (
        <div className="action-result">
          <h3>アクション</h3>
          <p>
            種別 <code>{result.action.action_type}</code>
            {result.identity_checked && '（本人確認ステップあり）'}
          </p>
          <p className="action-message">{result.action_result}</p>
        </div>
      )}

      <dl className="metrics">
        <div>
          <dt>groundedness（支持率）</dt>
          <dd>
            {result.groundedness.toFixed(2)}（判定可能 {result.groundedness_decided} 主張）
          </dd>
        </div>
        <div>
          <dt>全体信頼度</dt>
          <dd>{result.overall_confidence.toFixed(2)}</dd>
        </div>
        {result.source_agreement !== null && (
          <div>
            <dt>内部×Web 一致度</dt>
            <dd>{result.source_agreement.toFixed(2)}</dd>
          </div>
        )}
        {result.intent && (
          <div>
            <dt>意図分類</dt>
            <dd>{result.intent}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
