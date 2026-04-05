const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(API_KEY ? { "X-Api-Key": API_KEY } : {}),
    ...(options.headers as Record<string, string> || {}),
  };
  const res = await fetch(`${API_BASE}/api${path}`, { ...options, headers });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// Engine
export interface EngineControl {
  mode: string; phase: string; main_user_posting: boolean;
  phantom_engagement: boolean; commenting: boolean; replying: boolean; last_run: string | null;
}
export const getEngine = () => request<EngineControl>("/engine");
export const updateEngine = (data: Partial<EngineControl>) =>
  request<EngineControl>("/engine", { method: "PUT", body: JSON.stringify(data) });

// Schedule
export interface ActivityWindow {
  window_name: string; start_hour: number; end_hour: number; days_of_week: string; enabled: boolean;
}
export interface ScheduleConfig {
  mode: string; posts_per_week: number; comments_per_day_min: number; comments_per_day_max: number;
  phantom_comments_min: number; phantom_comments_max: number; min_delay_sec: number; max_likes_per_day: number;
}
export interface PlanAction {
  type: string; content_stream?: string; window?: string;
  target_category?: string; count?: number;
}
export interface WeeklyPlanDay {
  date: string; day: string; is_post_day: boolean; actions: PlanAction[];
}
export const getActivityWindows = () => request<ActivityWindow[]>("/schedule/windows");
export const getScheduleConfigs = () => request<ScheduleConfig[]>("/schedule/configs");
export const updateScheduleConfig = (mode: string, data: Partial<ScheduleConfig>) =>
  request("/schedule/configs/" + mode, { method: "PUT", body: JSON.stringify(data) });
export const getWeeklyPlan = () => request<WeeklyPlanDay[]>("/schedule/weekly-plan");

// Content
export interface ContentBankItem {
  item_id: number; category: string; post_type: string; draft: string;
  safety_flag: number; ready: boolean; last_used: string | null; notes: string | null;
}
export interface RepostBankItem {
  item_id: number; source_name: string; source_url: string; summary: string;
  commentary_prompt: string; safety_flag: number; last_used: string | null; notes: string | null;
}
export const getContentBank = () => request<ContentBankItem[]>("/content/bank?ready_only=false");
export const createContentItem = (data: Partial<ContentBankItem>) =>
  request("/content/bank", { method: "POST", body: JSON.stringify(data) });
export const updateContentItem = (id: number, data: Partial<ContentBankItem>) =>
  request(`/content/bank/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteContentItem = (id: number) =>
  request(`/content/bank/${id}`, { method: "DELETE" });
export const getRepostBank = () => request<RepostBankItem[]>("/content/reposts");
export const createRepostItem = (data: Partial<RepostBankItem>) =>
  request("/content/reposts", { method: "POST", body: JSON.stringify(data) });

// Targets
export interface CommentTarget {
  name: string; linkedin_url: string; category: string; priority: number;
  last_comment_date: string | null; notes: string | null;
}
export const getTargets = (category?: string) =>
  request<CommentTarget[]>("/targets" + (category ? `?category=${category}` : ""));
export const createTarget = (data: Partial<CommentTarget>) =>
  request("/targets", { method: "POST", body: JSON.stringify(data) });
export const updateTarget = (name: string, data: Partial<CommentTarget>) =>
  request(`/targets/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteTarget = (name: string) =>
  request(`/targets/${encodeURIComponent(name)}`, { method: "DELETE" });

// Templates
export interface CommentTemplate {
  template_id: string; template_text: string; tone: string; category: string;
  safety_flag: number; example_use: string; persona: string; use_count: number;
}
export const getTemplates = (persona?: string) =>
  request<CommentTemplate[]>("/templates" + (persona ? `?persona=${persona}` : ""));
export const createTemplate = (data: Partial<CommentTemplate>) =>
  request("/templates", { method: "POST", body: JSON.stringify(data) });
export const deleteTemplate = (id: string) =>
  request(`/templates/${id}`, { method: "DELETE" });

// Rules
export interface ReplyRule { condition_type: string; trigger: string; action: string; notes: string | null; }
export interface SafetyTerm { term: string; response: string; }
export const getReplyRules = () => request<ReplyRule[]>("/rules/reply");
export const createReplyRule = (data: Partial<ReplyRule>) =>
  request("/rules/reply", { method: "POST", body: JSON.stringify(data) });
export const deleteReplyRule = (trigger: string) =>
  request(`/rules/reply/${encodeURIComponent(trigger)}`, { method: "DELETE" });
export const getSafetyTerms = () => request<SafetyTerm[]>("/rules/safety");
export const createSafetyTerm = (data: SafetyTerm) =>
  request("/rules/safety", { method: "POST", body: JSON.stringify(data) });
export const deleteSafetyTerm = (term: string) =>
  request(`/rules/safety/${encodeURIComponent(term)}`, { method: "DELETE" });

// Personas
export interface PersonaSummary {
  name: string; display_name: string; persona: string;
  location: string | null; active_hours: Record<string, string> | null; behavior: Record<string, unknown> | null;
}
export const getPersonas = () => request<PersonaSummary[]>("/personas");
export const updatePersona = (name: string, data: Record<string, unknown>) =>
  request(`/personas/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(data) });

// Analytics
export interface DailySummary {
  date: string; comments_posted: number; posts_made: number; replies_sent: number;
  likes_given: number; last_action_time: string | null;
}
export interface EngagementTrend { date: string; comments: number; posts: number; replies: number; likes: number; }
export interface PersonaStats { persona: string; total_actions: number; comments: number; posts: number; replies: number; }
export const getTodaySummary = () => request<DailySummary>("/analytics/today");
export const getTrends = (days?: number) => request<EngagementTrend[]>(`/analytics/trends?days=${days || 30}`);
export const getPersonaAnalytics = (days?: number) => request<PersonaStats[]>(`/analytics/personas?days=${days || 30}`);

// History
export interface HistoryEntry {
  timestamp: string; module: string; action: string; target: string;
  result: string; safety: string; notes: string;
}
export interface HistoryResponse { entries: HistoryEntry[]; total: number; limit: number; offset: number; }
export const getHistory = (params: { limit?: number; offset?: number; action?: string; module?: string; date_from?: string; date_to?: string } = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
  return request<HistoryResponse>(`/history?${qs}`);
};
export const exportHistoryCsv = () => `${API_BASE}/api/history/export`;

// Alerts
export interface EngagementAlert {
  alert_id: string; commenter_name: string; commenter_url: string; comment_text: string;
  post_url: string; post_title: string; discovered_at: string; elapsed_minutes: number;
  urgency: string; responded: boolean;
}
export const getAlerts = (limit?: number) => request<EngagementAlert[]>(`/alerts?limit=${limit || 20}`);
export const markAlertResponded = (id: string) => request(`/alerts/${id}/respond`, { method: "POST" });
export const dismissAlert = (id: string) => request(`/alerts/${id}/dismiss`, { method: "POST" });

// Queue
export interface QueueItem {
  id: number; created_at: string | null; post_id: string; action_type: string;
  persona: string; target_name: string; target_url: string; draft_text: string;
  status: string; scheduled_time: string | null; executed_at: string | null; notes: string;
}
export interface QueueResponse { items: QueueItem[]; total: number; limit: number; offset: number; }
export interface QueueStats { total: number; [status: string]: number; }
export const getQueue = (params: { status?: string; limit?: number; offset?: number } = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
  return request<QueueResponse>(`/queue?${qs}`);
};
export const getQueueStats = () => request<QueueStats>("/queue/stats");
export const updateQueueItem = (id: number, data: { status?: string; draft_text?: string; notes?: string }) =>
  request(`/queue/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const createQueueItem = (data: { post_id?: string; persona?: string; draft_text: string; action_type?: string; target_url?: string; notes?: string }) =>
  request(`/queue`, { method: "POST", body: JSON.stringify(data) });

// Pipeline
export interface PipelineRun {
  id: number; started_at: string | null; completed_at: string | null;
  trigger_type: string; status: string; phase: string;
  posts_made: number; comments_made: number; replies_made: number;
  phantom_actions: number; errors: Record<string, unknown> | null; summary: string;
}
export interface PipelineRunsResponse { runs: PipelineRun[]; total: number; limit: number; offset: number; }
export interface PipelineError {
  source: string; run_id?: number; log_id?: number; timestamp: string | null;
  phase?: string; status?: string; errors?: Record<string, unknown> | null; summary?: string;
  module?: string; action?: string; target?: string; result?: string; notes?: string;
}
export interface ErrorsResponse {
  pipeline_errors: PipelineError[]; system_errors: PipelineError[];
  pipeline_error_count: number; system_error_count: number;
}
export const getPipelineRuns = (params: { limit?: number; offset?: number } = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
  return request<PipelineRunsResponse>(`/pipeline/runs?${qs}`);
};
export const triggerPipelineRun = (data: { trigger_type?: string; dry_run?: boolean } = {}) =>
  request<{ status: string; run_id: number; phase: string; mode: string; dry_run: boolean }>(
    "/pipeline/run", { method: "POST", body: JSON.stringify(data) }
  );
export const getPipelineErrors = (params: { limit?: number; offset?: number } = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
  return request<ErrorsResponse>(`/pipeline/errors?${qs}`);
};

// Feeds
export interface FeedSource {
  id: number; name: string; url: string; type: string;
  category: string; active: boolean; last_fetched: string | null; created_at: string | null;
}
export interface FeedsResponse { feeds: FeedSource[]; total: number; }
export const getFeeds = (activeOnly?: boolean) =>
  request<FeedsResponse>(`/feeds?active_only=${activeOnly || false}`);
export const createFeed = (data: { name: string; url: string; type?: string; category?: string; active?: boolean }) =>
  request("/feeds", { method: "POST", body: JSON.stringify(data) });
export const updateFeed = (id: number, data: Partial<FeedSource>) =>
  request(`/feeds/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteFeed = (id: number) =>
  request(`/feeds/${id}`, { method: "DELETE" });

// Persona Detail (single persona with full info)
export interface PersonaDetail {
  name: string; display_name: string; persona: string; system_prompt: string;
  session_dir: string; location: string | null; linkedin_url: string | null;
  active_hours: Record<string, string> | null; voice: Record<string, unknown> | null;
  engagement_rules: Record<string, unknown> | null; behavior: Record<string, unknown> | null;
}
export const getPersonaDetail = (name: string) =>
  request<PersonaDetail>(`/personas/${encodeURIComponent(name)}`);

// Heartbeat (per-persona autonomous scheduler)
export interface PersonaHeartbeatStatus {
  name: string; display_name: string; has_active_session: boolean;
  in_active_hours: boolean; active_hours: Record<string, string> | null;
  schedule: Record<string, number> | null; daily_stats: Record<string, number> | null;
  is_running: boolean;
}
export interface ScheduleUpdate {
  comments_per_cycle?: number; post_chance_per_cycle?: number;
  kyle_comment_chance?: number; cycle_interval_minutes?: number;
}
export const getHeartbeatStatus = () => request<PersonaHeartbeatStatus[]>("/heartbeat/status");
export const getPersonaSchedule = (name: string) =>
  request<{ name: string; display_name: string; schedule: Record<string, number>; active_hours: Record<string, string>; behavior: Record<string, unknown> }>(`/heartbeat/schedule/${encodeURIComponent(name)}`);
export const updatePersonaSchedule = (name: string, data: ScheduleUpdate) =>
  request(`/heartbeat/schedule/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(data) });
export const triggerHeartbeat = (name: string, data: { dry_run?: boolean; headless?: boolean } = {}) =>
  request<{ status: string; persona: string; display_name: string; dry_run: boolean }>(
    `/heartbeat/run/${encodeURIComponent(name)}`, { method: "POST", body: JSON.stringify(data) });
export const triggerAllHeartbeats = (data: { dry_run?: boolean; headless?: boolean } = {}) =>
  request<{ status: string; triggered: { name: string; display_name: string }[]; skipped: { name: string; display_name: string; reason: string }[]; dry_run: boolean }>(
    "/heartbeat/run-all", { method: "POST", body: JSON.stringify(data) });

// Kill Switch
export interface KillSwitchStatus { active: boolean; message: string; }
export const getKillSwitch = () => request<KillSwitchStatus>("/kill-switch");
export const activateKillSwitch = () => request<KillSwitchStatus>("/kill-switch/activate", { method: "POST" });
export const deactivateKillSwitch = () => request<KillSwitchStatus>("/kill-switch/deactivate", { method: "POST" });

// Leads
export interface Lead {
  name: string; title: string; company: string; score: number;
  reasons: string[]; source_url: string; interaction_type: string;
  comment_preview: string; discovered_at: string; status: string;
  interaction_count: number; last_seen: string | null; notes?: string;
}
export interface LeadsResponse { leads: Lead[]; total: number; }
export const getLeads = (status?: string) =>
  request<LeadsResponse>(`/leads${status ? `?status=${status}` : ""}`);
export const updateLead = (name: string, data: { status?: string; notes?: string }) =>
  request(`/leads/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify(data) });
export const deleteLead = (name: string) =>
  request(`/leads/${encodeURIComponent(name)}`, { method: "DELETE" });

// Pipeline Run Detail
export const getPipelineRun = (id: number) => request<PipelineRun>(`/pipeline/runs/${id}`);

// Connector (auto-connection engine)
export interface ConnectorStatus {
  sent_today: number; daily_limit: number; remaining: number;
  commenter_today: number; outbound_today: number;
  accepted_today: number; total_accepted: number; total_all_time: number;
  config: { commenter_priority: boolean; search_keywords: string[]; location: string; };
}
export interface ConnectionRequest {
  name: string; profile_url: string; headline: string; note: string;
  source: string; search_keyword?: string; post_context?: string;
  relevance_score?: number; timestamp: string; dry_run: boolean;
}
export interface ConnectionRequestsResponse {
  requests: ConnectionRequest[]; total: number; limit: number; offset: number;
}
export interface VoiceRecord {
  name: string; profile_url: string; script: string;
  audio_file: string | null; timestamp: string; dry_run: boolean;
}
export interface VoiceQueueResponse {
  pending: { name: string; profile_url: string; headline: string; source: string; sent_at: string; }[];
  sent: VoiceRecord[]; total_sent: number;
}
export const getConnectorStatus = () => request<ConnectorStatus>("/connector/status");
export const getConnectionRequests = (params: { source?: string; limit?: number; offset?: number } = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
  return request<ConnectionRequestsResponse>(`/connector/requests?${qs}`);
};
export const triggerConnector = (data: { dry_run?: boolean; commenter_only?: boolean; outbound_only?: boolean } = {}) =>
  request<{ status: string; dry_run: boolean }>("/connector/run", { method: "POST", body: JSON.stringify(data) });
export const getConnectorAcceptances = () =>
  request<{ pending_voice: number; voice_sent: number; recent_voice: VoiceRecord[] }>("/connector/acceptances");
export const getVoiceQueue = () => request<VoiceQueueResponse>("/connector/voice-queue");
export const triggerVoiceOutreach = (data: { dry_run?: boolean; max_messages?: number } = {}) =>
  request<{ status: string; dry_run: boolean }>("/connector/voice-run", { method: "POST", body: JSON.stringify(data) });
export const getConnectorConfig = () => request<Record<string, unknown>>("/connector/config");
export const updateConnectorConfig = (updates: Record<string, unknown>) =>
  request("/connector/config", { method: "PUT", body: JSON.stringify(updates) });

// DM Auto-Responder
export interface DmResponderStatus {
  replied_today: number; daily_limit: number; queue_depth: number;
  queue: DmQueueEntry[]; total_replied: number;
  recent_replies: DmSentReply[]; intent_breakdown: Record<string, number>;
}
export interface DmQueueEntry {
  sender: string; profile_url: string; thread_index: number; intent: string;
  reply_text: string; last_incoming_text: string;
  queued_at: string; send_at: string; sent: boolean;
}
export interface DmSentReply {
  sender: string; intent: string; reply_text: string; sent_at: string;
}
export interface DmRepliesResponse {
  replies: DmSentReply[]; total: number; limit: number; offset: number;
}
export const getDmResponderStatus = () => request<DmResponderStatus>("/dm-responder/status");
export const getDmReplies = (params: { limit?: number; offset?: number } = {}) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
  return request<DmRepliesResponse>(`/dm-responder/replies?${qs}`);
};
export const getDmQueue = () => request<{ queue: DmQueueEntry[]; count: number }>("/dm-responder/queue");
export const triggerDmResponder = (data: { dry_run?: boolean; max_replies?: number } = {}) =>
  request<{ status: string; dry_run: boolean }>("/dm-responder/run", { method: "POST", body: JSON.stringify(data) });
export const cancelDmQueueItem = (index: number) =>
  request<{ status: string }>(`/dm-responder/queue/${index}`, { method: "DELETE" });

// Health
export const healthCheck = () => request<{ status: string }>("/health");
