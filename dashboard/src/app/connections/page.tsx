"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getConnectorStatus,
  getConnectionRequests,
  getVoiceQueue,
  getDmResponderStatus,
  triggerConnector,
  triggerVoiceOutreach,
  triggerDmResponder,
  cancelDmQueueItem,
  type ConnectorStatus,
  type ConnectionRequest,
  type VoiceQueueResponse,
  type DmResponderStatus,
  type DmQueueEntry,
  type DmSentReply,
} from "@/lib/api";
import { Link2, Users, Search, Mic, Play, Zap, ExternalLink, Clock3, UserPlus, UserCheck, Volume2, RefreshCw, MessageCircle, X, Inbox } from "lucide-react";

// --- Status budget bar ---
function BudgetBar({ sent, limit }: { sent: number; limit: number }) {
  const pct = limit > 0 ? Math.min((sent / limit) * 100, 100) : 0;
  const color = pct > 90 ? "bg-[#ef4444]" : pct > 60 ? "bg-[#f59e0b]" : "bg-[#06b6d4]";
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-[#73808c]"><span className="font-mono-data">{sent}</span> / <span className="font-mono-data">{limit}</span> requests sent today</span>
        <span className="text-[#a7b0b8] font-mono-data">{limit - sent} remaining</span>
      </div>
      <div className="h-2 bg-[#1b2024] rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// --- Stat card ---
function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-card border rounded-[10px] p-4 flex items-center gap-4">
      <div className="h-10 w-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}10` }}>
        <Icon className="h-5 w-5" style={{ color }} />
      </div>
      <div>
        <p className="text-2xl font-semibold font-mono-data">{value}</p>
        <p className="text-[11px] text-[#73808c] uppercase tracking-wider font-medium">{label}</p>
      </div>
    </div>
  );
}

// --- Source badge ---
function SourceBadge({ source }: { source: string }) {
  if (source === "commenter") {
    return <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-[#06b6d4]/10 text-[#06b6d4] border border-[#06b6d4]/20"><UserPlus className="h-3 w-3" />Commenter</span>;
  }
  return <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20"><Search className="h-3 w-3" />Outbound</span>;
}

// --- Timestamp display ---
function TimeAgo({ timestamp }: { timestamp: string }) {
  if (!timestamp) return <span className="text-[#73808c]">-</span>;
  const d = new Date(timestamp);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  let text: string;
  if (diff < 60) text = "just now";
  else if (diff < 3600) text = `${Math.floor(diff / 60)}m ago`;
  else if (diff < 86400) text = `${Math.floor(diff / 3600)}h ago`;
  else text = `${Math.floor(diff / 86400)}d ago`;
  return <span className="text-[#73808c] text-xs font-mono-data" title={d.toLocaleString()}>{text}</span>;
}

// --- Request row ---
function RequestRow({ req }: { req: ConnectionRequest }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-b border-[#2a3138]/50 last:border-0">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left px-4 py-3 hover:bg-[#161a1d] transition-colors flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-[#1b2024] flex items-center justify-center text-xs font-bold text-[#a7b0b8] shrink-0">
          {req.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{req.name}</span>
            <SourceBadge source={req.source} />
            {req.dry_run && <span className="text-xs px-1.5 py-0.5 rounded bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20">Dry Run</span>}
          </div>
          <p className="text-xs text-[#73808c] truncate">{req.headline}</p>
        </div>
        <div className="shrink-0 flex items-center gap-3">
          {req.relevance_score !== undefined && req.relevance_score > 0 && (
            <span className="text-xs font-mono-data px-1.5 py-0.5 rounded bg-[#22c55e]/10 text-[#22c55e]" title="Relevance score">
              {req.relevance_score}
            </span>
          )}
          <TimeAgo timestamp={req.timestamp} />
          <a href={req.profile_url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="text-[#73808c] hover:text-[#f3f5f7] transition-colors">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-3 pl-15 space-y-2">
          <div className="bg-[#090a0b] border border-[#2a3138] rounded-lg p-3">
            <p className="text-[11px] text-[#73808c] uppercase tracking-wider mb-1">Connection note</p>
            <p className="text-sm text-[#a7b0b8]">{req.note}</p>
          </div>
          {req.post_context && (
            <div className="text-xs text-[#73808c]">
              <span className="font-medium text-[#a7b0b8]">Post context:</span> {req.post_context}
            </div>
          )}
          {req.search_keyword && (
            <div className="text-xs text-[#73808c]">
              <span className="font-medium text-[#a7b0b8]">Search keyword:</span> <span className="font-mono-data">{req.search_keyword}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Voice queue item ---
function VoicePendingRow({ item }: { item: VoiceQueueResponse["pending"][0] }) {
  return (
    <div className="px-4 py-3 flex items-center gap-3 border-b border-[#2a3138]/50 last:border-0">
      <div className="h-8 w-8 rounded-full bg-[#1b2024] flex items-center justify-center text-xs font-bold text-[#a7b0b8] shrink-0">
        {item.name.split(" ").map(n => n[0]).join("").slice(0, 2)}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.name}</p>
        <p className="text-xs text-[#73808c] truncate">{item.headline}</p>
      </div>
      <SourceBadge source={item.source} />
      <TimeAgo timestamp={item.sent_at} />
    </div>
  );
}

function VoiceSentRow({ item }: { item: VoiceQueueResponse["sent"][0] }) {
  const [showScript, setShowScript] = useState(false);
  return (
    <div className="border-b border-[#2a3138]/50 last:border-0">
      <button onClick={() => setShowScript(!showScript)} className="w-full text-left px-4 py-3 hover:bg-[#161a1d] transition-colors flex items-center gap-3">
        <Volume2 className="h-4 w-4 text-[#22c55e] shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{item.name}</p>
          <p className="text-xs text-[#73808c] truncate">{item.script.slice(0, 80)}...</p>
        </div>
        <TimeAgo timestamp={item.timestamp} />
      </button>
      {showScript && (
        <div className="px-4 pb-3 pl-11">
          <div className="bg-[#090a0b] border border-[#2a3138] rounded-lg p-3">
            <p className="text-[11px] text-[#73808c] uppercase tracking-wider mb-1">Voice script</p>
            <p className="text-sm leading-relaxed text-[#a7b0b8]">{item.script}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Intent badge ---
const INTENT_COLORS: Record<string, string> = {
  greeting: "bg-[#06b6d4]/10 text-[#06b6d4] border-[#06b6d4]/20",
  job_opportunity: "bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20",
  business_inquiry: "bg-[#a78bfa]/10 text-[#a78bfa] border-[#a78bfa]/20",
  collaboration: "bg-[#2dd4bf]/10 text-[#2dd4bf] border-[#2dd4bf]/20",
  question: "bg-[#60a5fa]/10 text-[#60a5fa] border-[#60a5fa]/20",
  compliment: "bg-[#f472b6]/10 text-[#f472b6] border-[#f472b6]/20",
  sales_pitch: "bg-[#fb923c]/10 text-[#fb923c] border-[#fb923c]/20",
  spam: "bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20",
  follow_up: "bg-[#a7b0b8]/10 text-[#a7b0b8] border-[#a7b0b8]/20",
};
function IntentBadge({ intent }: { intent: string }) {
  const colors = INTENT_COLORS[intent] || "bg-[#a7b0b8]/10 text-[#a7b0b8] border-[#a7b0b8]/20";
  return <span className={`text-xs px-2 py-0.5 rounded-full border ${colors}`}>{intent.replace("_", " ")}</span>;
}

// --- DM queue row ---
function DmQueueRow({ entry, index, onCancel }: { entry: DmQueueEntry; index: number; onCancel: (i: number) => void }) {
  const [expanded, setExpanded] = useState(false);
  const sendAt = new Date(entry.send_at);
  const now = new Date();
  const minsLeft = Math.max(0, Math.round((sendAt.getTime() - now.getTime()) / 60000));
  return (
    <div className="border-b border-[#2a3138]/50 last:border-0">
      <div className="px-4 py-3 flex items-center gap-3">
        <button onClick={() => setExpanded(!expanded)} className="flex-1 text-left flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 rounded-full bg-[#1b2024] flex items-center justify-center text-xs font-bold text-[#a7b0b8] shrink-0">
            {entry.sender.split(" ").map(n => n[0]).join("").slice(0, 2)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{entry.sender}</span>
              <IntentBadge intent={entry.intent} />
            </div>
            <p className="text-xs text-[#73808c] truncate">{entry.reply_text.slice(0, 80)}...</p>
          </div>
        </button>
        <span className="text-xs text-[#f59e0b] font-mono-data shrink-0">{minsLeft > 0 ? `${minsLeft}m` : "sending..."}</span>
        <button onClick={() => onCancel(index)} className="p-1 rounded hover:bg-[#ef4444]/10 text-[#ef4444] transition-colors" title="Cancel">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      {expanded && (
        <div className="px-4 pb-3 pl-15 space-y-2">
          <div className="bg-[#090a0b] border border-[#2a3138] rounded-lg p-3 space-y-3">
            <div>
              <p className="text-[11px] text-[#73808c] uppercase tracking-wider mb-0.5">Their message</p>
              <p className="text-sm text-[#a7b0b8]">{entry.last_incoming_text}</p>
            </div>
            <div>
              <p className="text-[11px] text-[#73808c] uppercase tracking-wider mb-0.5">Your reply</p>
              <p className="text-sm">{entry.reply_text}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- DM sent row ---
function DmSentRow({ reply }: { reply: DmSentReply }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-b border-[#2a3138]/50 last:border-0">
      <button onClick={() => setExpanded(!expanded)} className="w-full text-left px-4 py-3 hover:bg-[#161a1d] transition-colors flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-[#1b2024] flex items-center justify-center text-xs font-bold text-[#a7b0b8] shrink-0">
          {reply.sender.split(" ").map(n => n[0]).join("").slice(0, 2)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{reply.sender}</span>
            <IntentBadge intent={reply.intent} />
          </div>
          <p className="text-xs text-[#73808c] truncate">{reply.reply_text.slice(0, 80)}...</p>
        </div>
        <TimeAgo timestamp={reply.sent_at} />
      </button>
      {expanded && (
        <div className="px-4 pb-3 pl-15">
          <div className="bg-[#090a0b] border border-[#2a3138] rounded-lg p-3">
            <p className="text-[11px] text-[#73808c] uppercase tracking-wider mb-1">Reply sent</p>
            <p className="text-sm leading-relaxed text-[#a7b0b8]">{reply.reply_text}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Tab system ---
type Tab = "requests" | "voice" | "dms";

export default function ConnectionsPage() {
  const [status, setStatus] = useState<ConnectorStatus | null>(null);
  const [requests, setRequests] = useState<ConnectionRequest[]>([]);
  const [requestsTotal, setRequestsTotal] = useState(0);
  const [voiceQueue, setVoiceQueue] = useState<VoiceQueueResponse | null>(null);
  const [dmStatus, setDmStatus] = useState<DmResponderStatus | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("requests");
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [s, r, v, dm] = await Promise.all([
        getConnectorStatus(),
        getConnectionRequests({ source: sourceFilter || undefined, limit: 50 }),
        getVoiceQueue(),
        getDmResponderStatus(),
      ]);
      setStatus(s);
      setRequests(r.requests);
      setRequestsTotal(r.total);
      setVoiceQueue(v);
      setDmStatus(dm);
    } catch (e) {
      console.error("Failed to fetch connector data:", e);
    } finally {
      setLoading(false);
    }
  }, [sourceFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCancelDm = async (index: number) => {
    try {
      await cancelDmQueueItem(index);
      fetchData();
    } catch (e) {
      console.error("Failed to cancel DM:", e);
    }
  };

  const handleTrigger = async (action: string) => {
    setActionLoading(action);
    try {
      if (action === "commenter") await triggerConnector({ commenter_only: true });
      else if (action === "outbound") await triggerConnector({ outbound_only: true });
      else if (action === "all") await triggerConnector();
      else if (action === "voice") await triggerVoiceOutreach();
      else if (action === "dry-run") await triggerConnector({ dry_run: true });
      else if (action === "dm-scan") await triggerDmResponder();
      setTimeout(() => fetchData(), 2000);
    } catch (e) {
      console.error("Trigger failed:", e);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="h-6 w-6 animate-spin text-[#73808c]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2.5">
            <Link2 className="h-5 w-5 text-[#06b6d4]" /> Connections
          </h1>
          <p className="text-sm text-[#73808c] mt-1">Auto-connection engine with voice outreach &amp; DM replies</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleTrigger("dry-run")}
            disabled={!!actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[#2a3138] text-[#a7b0b8] hover:bg-[#161a1d] transition-colors disabled:opacity-50"
          >
            <Play className="h-3 w-3" /> Dry Run
          </button>
          <button
            onClick={() => handleTrigger("all")}
            disabled={!!actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-[#06b6d4] hover:bg-[#22d3ee] text-[#090a0b] font-medium transition-colors disabled:opacity-50"
          >
            <Zap className="h-3 w-3" /> Run Connector
          </button>
          <button onClick={() => fetchData()} className="p-1.5 rounded-lg hover:bg-[#161a1d] text-[#73808c] hover:text-[#f3f5f7] transition-colors" title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Budget bar */}
      {status && <BudgetBar sent={status.sent_today} limit={status.daily_limit} />}

      {/* Stat cards */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard label="Sent Today" value={status.sent_today} icon={UserPlus} color="#06b6d4" />
          <StatCard label="Accepted Today" value={status.accepted_today} icon={UserCheck} color="#22c55e" />
          <StatCard label="From Commenters" value={status.commenter_today} icon={Users} color="#22d3ee" />
          <StatCard label="From Outbound" value={status.outbound_today} icon={Search} color="#f59e0b" />
          <StatCard label="All Time" value={status.total_all_time} icon={Link2} color="#a7b0b8" />
        </div>
      )}

      {/* Action bar */}
      <div className="flex flex-wrap items-center gap-2 p-3 bg-card border rounded-[10px]">
        <span className="text-[11px] text-[#73808c] uppercase tracking-wider font-semibold mr-2">Quick Actions</span>
        <button onClick={() => handleTrigger("commenter")} disabled={!!actionLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[#06b6d4]/20 text-[#06b6d4] hover:bg-[#06b6d4]/5 transition-colors disabled:opacity-50">
          <UserPlus className="h-3 w-3" />
          {actionLoading === "commenter" ? "Running..." : "Connect Commenters"}
        </button>
        <button onClick={() => handleTrigger("outbound")} disabled={!!actionLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[#f59e0b]/20 text-[#f59e0b] hover:bg-[#f59e0b]/5 transition-colors disabled:opacity-50">
          <Search className="h-3 w-3" />
          {actionLoading === "outbound" ? "Running..." : "Outbound Search"}
        </button>
        <button onClick={() => handleTrigger("voice")} disabled={!!actionLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[#22c55e]/20 text-[#22c55e] hover:bg-[#22c55e]/5 transition-colors disabled:opacity-50">
          <Mic className="h-3 w-3" />
          {actionLoading === "voice" ? "Running..." : "Send Voice Messages"}
        </button>
        <button onClick={() => handleTrigger("dm-scan")} disabled={!!actionLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[#06b6d4]/20 text-[#06b6d4] hover:bg-[#06b6d4]/5 transition-colors disabled:opacity-50">
          <Inbox className="h-3 w-3" />
          {actionLoading === "dm-scan" ? "Scanning..." : "Scan DMs"}
        </button>

        {status && status.config.search_keywords.length > 0 && (
          <div className="ml-auto flex items-center gap-1 flex-wrap">
            {status.config.search_keywords.slice(0, 4).map(kw => (
              <span key={kw} className="text-[10px] px-1.5 py-0.5 rounded bg-[#1b2024] text-[#73808c] font-mono-data">{kw}</span>
            ))}
            {status.config.search_keywords.length > 4 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1b2024] text-[#73808c] font-mono-data">
                +{status.config.search_keywords.length - 4}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#2a3138]">
        {([
          { key: "requests" as Tab, label: `Connection Requests (${requestsTotal})`, color: "#06b6d4" },
          { key: "voice" as Tab, label: `Voice Messages (${voiceQueue?.total_sent || 0})`, color: "#22c55e" },
          { key: "dms" as Tab, label: `DM Replies (${dmStatus?.total_replied || 0})`, color: "#06b6d4" },
        ] as const).map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? `text-[${tab.color}]`
                : "border-transparent text-[#73808c] hover:text-[#f3f5f7]"
            }`}
            style={activeTab === tab.key ? { borderColor: tab.color, color: tab.color } : {}}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "requests" && (
        <div className="space-y-3">
          {/* Filter */}
          <div className="flex gap-2">
            {["", "commenter", "outbound_search"].map(src => (
              <button
                key={src}
                onClick={() => setSourceFilter(src)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                  sourceFilter === src
                    ? "bg-[#1b2024] border-[#2a3138] text-[#f3f5f7]"
                    : "border-[#2a3138]/50 text-[#73808c] hover:text-[#f3f5f7]"
                }`}
              >
                {src === "" ? "All" : src === "commenter" ? "Commenters" : "Outbound"}
              </button>
            ))}
          </div>

          {/* Request list */}
          <div className="bg-card border rounded-[10px] overflow-hidden">
            {requests.length === 0 ? (
              <div className="p-8 text-center">
                <UserPlus className="h-8 w-8 mx-auto mb-2 text-[#2a3138]" />
                <p className="text-sm text-[#a7b0b8]">No connection requests yet</p>
                <p className="text-xs text-[#73808c] mt-1">Run the connector to start growing your network</p>
              </div>
            ) : (
              requests.map((req, i) => <RequestRow key={`${req.profile_url}-${i}`} req={req} />)
            )}
          </div>
        </div>
      )}

      {activeTab === "voice" && voiceQueue && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-card border rounded-[10px] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#2a3138] flex items-center gap-2">
              <Clock3 className="h-4 w-4 text-[#f59e0b]" />
              <h3 className="text-sm font-medium">Pending Follow-ups</h3>
              <span className="text-xs text-[#73808c] font-mono-data ml-auto">{voiceQueue.pending.length}</span>
            </div>
            {voiceQueue.pending.length === 0 ? (
              <div className="p-6 text-center text-[#73808c] text-sm">No pending voice follow-ups</div>
            ) : (
              voiceQueue.pending.map((item, i) => <VoicePendingRow key={`${item.profile_url}-${i}`} item={item} />)
            )}
          </div>

          <div className="bg-card border rounded-[10px] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#2a3138] flex items-center gap-2">
              <Volume2 className="h-4 w-4 text-[#22c55e]" />
              <h3 className="text-sm font-medium">Sent Messages</h3>
              <span className="text-xs text-[#73808c] font-mono-data ml-auto">{voiceQueue.total_sent}</span>
            </div>
            {voiceQueue.sent.length === 0 ? (
              <div className="p-6 text-center text-[#73808c] text-sm">No voice messages sent yet</div>
            ) : (
              voiceQueue.sent.map((item, i) => <VoiceSentRow key={`${item.profile_url}-${i}`} item={item} />)
            )}
          </div>
        </div>
      )}

      {activeTab === "dms" && (
        <div className="space-y-4">
          {/* DM stat cards */}
          {dmStatus && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Replied Today" value={dmStatus.replied_today} icon={MessageCircle} color="#06b6d4" />
              <StatCard label="Queue Depth" value={dmStatus.queue_depth} icon={Clock3} color="#f59e0b" />
              <StatCard label="Daily Limit" value={dmStatus.daily_limit} icon={Inbox} color="#a7b0b8" />
              <StatCard label="Total Replied" value={dmStatus.total_replied} icon={MessageCircle} color="#22c55e" />
            </div>
          )}

          {/* Intent breakdown */}
          {dmStatus && dmStatus.intent_breakdown && Object.keys(dmStatus.intent_breakdown).length > 0 && (
            <div className="flex flex-wrap gap-2 p-3 bg-card border rounded-[10px]">
              <span className="text-[11px] text-[#73808c] uppercase tracking-wider font-semibold mr-1">Intents</span>
              {Object.entries(dmStatus.intent_breakdown).sort((a, b) => b[1] - a[1]).map(([intent, count]) => (
                <span key={intent} className="inline-flex items-center gap-1">
                  <IntentBadge intent={intent} />
                  <span className="text-xs text-[#73808c] font-mono-data">{count}</span>
                </span>
              ))}
            </div>
          )}

          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-card border rounded-[10px] overflow-hidden">
              <div className="px-4 py-3 border-b border-[#2a3138] flex items-center gap-2">
                <Clock3 className="h-4 w-4 text-[#f59e0b]" />
                <h3 className="text-sm font-medium">Queued Replies</h3>
                <span className="text-xs text-[#73808c] font-mono-data ml-auto">{dmStatus?.queue?.length || 0}</span>
              </div>
              {!dmStatus?.queue?.length ? (
                <div className="p-6 text-center text-[#73808c] text-sm">No replies queued</div>
              ) : (
                dmStatus.queue.filter(e => !e.sent).map((entry, i) => (
                  <DmQueueRow key={`${entry.sender}-${i}`} entry={entry} index={i} onCancel={handleCancelDm} />
                ))
              )}
            </div>

            <div className="bg-card border rounded-[10px] overflow-hidden">
              <div className="px-4 py-3 border-b border-[#2a3138] flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-[#06b6d4]" />
                <h3 className="text-sm font-medium">Recent Replies</h3>
                <span className="text-xs text-[#73808c] font-mono-data ml-auto">{dmStatus?.recent_replies?.length || 0}</span>
              </div>
              {!dmStatus?.recent_replies?.length ? (
                <div className="p-6 text-center text-[#73808c] text-sm">No DM replies sent yet</div>
              ) : (
                dmStatus.recent_replies.map((reply, i) => (
                  <DmSentRow key={`${reply.sender}-${reply.sent_at}-${i}`} reply={reply} />
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
