// GRACE-Support（問い合わせ → 回答）のタブ本体。
// App.tsx から切り出したもので、パイプラインの配線は変えていない。
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import {
  confirmIntervention,
  fetchVerticals,
  startQuery,
  subscribeStream,
} from '../api/client';
import { initialJobState, jobReducer } from '../state/jobReducer';
import type { QueryParams, VerticalInfo } from '../types';
import { AnswerCard } from './AnswerCard';
import { ConfirmModal } from './ConfirmModal';
import { QueryForm } from './QueryForm';
import { StepTimeline } from './StepTimeline';

export function SupportPanel() {
  const [state, dispatch] = useReducer(jobReducer, initialJobState);
  const [verticals, setVerticals] = useState<VerticalInfo[]>([]);
  const [confirming, setConfirming] = useState(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    fetchVerticals()
      .then(setVerticals)
      .catch(() => setVerticals([]));
    return () => unsubscribeRef.current?.();
  }, []);

  const submit = useCallback(async (params: QueryParams) => {
    unsubscribeRef.current?.();
    try {
      const { job_id } = await startQuery(params);
      dispatch({ type: 'started', jobId: job_id });
      unsubscribeRef.current = subscribeStream(
        job_id,
        (event) => dispatch({ type: 'event', event }),
        (message) => dispatch({ type: 'failed', message }),
        'support',
      );
    } catch (error) {
      dispatch({
        type: 'failed',
        message: error instanceof Error ? error.message : String(error),
      });
    }
  }, []);

  const respond = useCallback(
    async (approve: boolean) => {
      if (!state.jobId || !state.intervention) return;
      setConfirming(true);
      try {
        await confirmIntervention(state.jobId, state.intervention.intervention_id, approve);
        dispatch({ type: 'confirm_sent' });
      } catch (error) {
        dispatch({
          type: 'failed',
          message: error instanceof Error ? error.message : String(error),
        });
      } finally {
        setConfirming(false);
      }
    },
    [state.jobId, state.intervention],
  );

  return (
    <>
      <p className="panel-lead">
        内部RAG＋出典 / Web裏取り・相互検証 / アクション＋HITL 承認
      </p>

      <QueryForm verticals={verticals} running={state.phase === 'running'} onSubmit={submit} />

      {state.error && <div className="error-banner">{state.error}</div>}
      {state.phase === 'running' && !state.intervention && (
        <div className="running-banner">
          実行中… ステップ進捗は下のタイムラインに逐次表示されます
        </div>
      )}

      <StepTimeline state={state} />
      {state.result && <AnswerCard result={state.result} />}

      {state.intervention && (
        <ConfirmModal
          intervention={state.intervention}
          actionStep={state.steps.action}
          submitting={confirming}
          onRespond={respond}
        />
      )}
    </>
  );
}
