const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type AlertPayload = {
  alert_id: string; commenter_name: string; comment_text: string;
  post_url: string; elapsed_minutes: number; urgency: string;
};

export type AlertMessage = { type: "alerts"; data: AlertPayload[] };

export function createAlertSocket(
  onMessage: (msg: AlertMessage) => void,
  onError?: (err: Event) => void,
) {
  const ws = new WebSocket(`${WS_BASE}/api/alerts/ws`);
  ws.onmessage = (event) => {
    try { onMessage(JSON.parse(event.data)); } catch {}
  };
  ws.onerror = (err) => onError?.(err);
  ws.onclose = () => {
    // Auto-reconnect after 5s
    setTimeout(() => createAlertSocket(onMessage, onError), 5000);
  };
  return ws;
}

// --- Pipeline status WebSocket ---

import type { PipelineRun } from "@/lib/api";

export type PipelineStatusMessage = {
  type: "pipeline_status";
  active_run: PipelineRun | null;
  active_run_id: number | null;
  recent_runs: PipelineRun[];
  running_task_ids: number[];
  live_output: string[];
};

export function createPipelineSocket(
  onMessage: (msg: PipelineStatusMessage) => void,
  onError?: (err: Event) => void,
) {
  const ws = new WebSocket(`${WS_BASE}/api/pipeline/ws`);
  ws.onmessage = (event) => {
    try { onMessage(JSON.parse(event.data)); } catch {}
  };
  ws.onerror = (err) => onError?.(err);
  ws.onclose = () => {
    setTimeout(() => createPipelineSocket(onMessage, onError), 5000);
  };
  return ws;
}
