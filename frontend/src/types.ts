// バックエンド（backend/app/schemas.py）と対応する型定義。

export type Decision = 'answer' | 'escalate';

/** SSE（/api/support/stream/{job_id}）で届く進捗イベント。 */
export interface SupportEvent {
  seq?: number;
  ts?: number;
  type: 'step' | 'log' | 'intervention' | 'result' | 'error' | 'done';
  step?: string | null;
  status?: string | null;
  title?: string;
  message?: string;
  data?: Record<string, unknown>;
}

export interface ActionRequestInfo {
  action_type: string;
  args: Record<string, unknown>;
  requires_confirmation: boolean;
}

/** SupportResult（backend/app/core/support_agent.py）の JSON 表現。 */
export interface SupportResult {
  answer: string | null;
  citations: string[];
  groundedness: number;
  groundedness_decided: number;
  decision: Decision;
  warning: boolean;
  used_web: boolean;
  source_agreement: number | null;
  contradiction: boolean;
  action: ActionRequestInfo | null;
  action_result: string | null;
  vertical: string | null;
  overall_confidence: number;
  intent: string | null;
  forced_escalate: boolean;
  identity_checked: boolean;
  no_info_detected: boolean;
  web_reused: boolean;
}

export interface VerticalInfo {
  id: string;
  name: string;
  collections: string[];
  escalate_keywords: string[];
  action_map: Record<string, string>;
  require_identity: boolean;
  notify_th: number | null;
  confirm_th: number | null;
  prompt_addendum: string;
}

/** HITL CONFIRM の承認待ち（intervention イベントの data）。 */
export interface InterventionInfo {
  intervention_id: string;
  message: string;
  reason?: string | null;
  options?: string[] | null;
  confidence_score?: number | null;
  timeout_seconds?: number;
}

export interface QueryParams {
  query: string;
  vertical: string | null;
  dry_run: boolean;
  use_web: boolean;
  do_action: boolean;
  verbose: boolean;
}
