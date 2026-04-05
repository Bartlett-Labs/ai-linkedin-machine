"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import {
  getPersonaAnalytics,
  getHeartbeatStatus,
  getHistory,
} from "@/lib/api";
import type { PersonaStats, PersonaHeartbeatStatus, HistoryResponse } from "@/lib/api";
import {
  Activity, MessageSquare, FileText, Reply, User,
  TrendingUp, BarChart3, Clock, Wifi, WifiOff, Loader2,
} from "lucide-react";

const PERSONA_ACCENTS: Record<string, string> = {
  "The Visionary Advisor": "#06b6d4",
  "The Deep Learner": "#2dd4bf",
  "The Skeptical Senior Dev": "#f59e0b",
  "The Corporate Compliance Officer": "#a7b0b8",
  "The Creative Tinkerer": "#22c55e",
  "The ROI-Driven Manager": "#fb923c",
  MainUser: "#06b6d4",
};

function BarSegment({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-full rounded-sm transition-all duration-700 ease-out" style={{ width: `${pct}%` }}>
      <div className="h-full rounded-sm" style={{ backgroundColor: color }} />
    </div>
  );
}

function PersonaActivityCard({
  stats, heartbeat, maxActions,
}: {
  stats: PersonaStats; heartbeat?: PersonaHeartbeatStatus; maxActions: number;
}) {
  const accent = PERSONA_ACCENTS[stats.persona] || "#f3f5f7";
  const displayName = heartbeat?.display_name || stats.persona;
  const pct = maxActions > 0 ? Math.round((stats.total_actions / maxActions) * 100) : 0;

  return (
    <Card className="border transition-all hover:shadow-md" style={{ borderColor: `${accent}20`, backgroundColor: `${accent}08` }}>
      <CardContent className="pt-4 pb-3 space-y-3">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-[#090a0b]/60 border border-[#2a3138]/50 flex items-center justify-center">
              <User className="h-4 w-4" style={{ color: accent }} />
            </div>
            <div>
              <h3 className="font-semibold text-sm">{displayName}</h3>
              {stats.persona !== displayName && (
                <p className="text-[10px] text-[#73808c]">{stats.persona}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {heartbeat && (
              heartbeat.has_active_session ? (
                <Wifi className="h-3.5 w-3.5 text-[#22c55e]" />
              ) : (
                <WifiOff className="h-3.5 w-3.5 text-[#73808c]/50" />
              )
            )}
            <Badge variant="outline" className="font-mono-data text-xs">
              {stats.total_actions}
            </Badge>
          </div>
        </div>

        {/* Activity bar */}
        <div className="space-y-1">
          <div className="h-2.5 bg-[#1b2024] rounded-full overflow-hidden flex gap-px">
            <BarSegment value={stats.comments} max={maxActions} color="#06b6d4" />
            <BarSegment value={stats.posts} max={maxActions} color="#22c55e" />
            <BarSegment value={stats.replies} max={maxActions} color="#f59e0b" />
          </div>
          <div className="flex items-center justify-between text-[10px] text-[#73808c]">
            <span className="font-mono-data">{pct}%</span>
            <span>of top performer &middot; 30d</span>
          </div>
        </div>

        {/* Breakdown */}
        <div className="grid grid-cols-3 gap-2">
          <div className="text-center p-2 rounded-lg bg-[#090a0b]/40">
            <div className="flex items-center justify-center gap-1 mb-0.5">
              <MessageSquare className="h-3 w-3 text-[#06b6d4]" />
              <span className="text-xs text-[#73808c]">Comments</span>
            </div>
            <span className="text-lg font-semibold font-mono-data">{stats.comments}</span>
          </div>
          <div className="text-center p-2 rounded-lg bg-[#090a0b]/40">
            <div className="flex items-center justify-center gap-1 mb-0.5">
              <FileText className="h-3 w-3 text-[#22c55e]" />
              <span className="text-xs text-[#73808c]">Posts</span>
            </div>
            <span className="text-lg font-semibold font-mono-data">{stats.posts}</span>
          </div>
          <div className="text-center p-2 rounded-lg bg-[#090a0b]/40">
            <div className="flex items-center justify-center gap-1 mb-0.5">
              <Reply className="h-3 w-3 text-[#f59e0b]" />
              <span className="text-xs text-[#73808c]">Replies</span>
            </div>
            <span className="text-lg font-semibold font-mono-data">{stats.replies}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RecentActivityTable({ entries }: { entries: { timestamp: string; module: string; action: string; target: string; result: string; notes: string }[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-[#73808c] py-4 text-center">No recent activity</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#2a3138]">
            <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Time</th>
            <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Module</th>
            <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Action</th>
            <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Target</th>
            <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Result</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i} className="border-b border-[#2a3138]/30 hover:bg-[#161a1d] transition-colors">
              <td className="py-2.5 px-3 font-mono-data text-xs text-[#73808c] whitespace-nowrap">
                {e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "-"}
              </td>
              <td className="py-2.5 px-3">
                <Badge variant="outline" className="text-[10px] font-mono-data">{e.module}</Badge>
              </td>
              <td className="py-2.5 px-3 text-xs text-[#a7b0b8]">{e.action}</td>
              <td className="py-2.5 px-3 text-xs truncate max-w-[200px] text-[#73808c]">{e.target}</td>
              <td className="py-2.5 px-3">
                <Badge className={`text-[10px] ${
                  e.result?.toLowerCase().includes("success") || e.result?.toLowerCase().includes("ok")
                    ? "bg-[#22c55e]/20 text-[#22c55e]"
                    : e.result?.toLowerCase().includes("fail") || e.result?.toLowerCase().includes("error")
                    ? "bg-[#ef4444]/20 text-[#ef4444]"
                    : "bg-[#1b2024] text-[#73808c]"
                }`}>
                  {e.result || "-"}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PhantomActivityPage() {
  const [days, setDays] = useState(30);
  const personaStats = useApi<PersonaStats[]>(() => getPersonaAnalytics(days), [days]);
  const heartbeat = useApi<PersonaHeartbeatStatus[]>(getHeartbeatStatus);
  const recentActivity = useApi<HistoryResponse>(() => getHistory({ limit: 25 }));

  const maxActions = personaStats.data
    ? Math.max(...personaStats.data.map((s) => s.total_actions), 1)
    : 1;

  const totalStats = personaStats.data?.reduce(
    (acc, s) => ({
      total: acc.total + s.total_actions,
      comments: acc.comments + s.comments,
      posts: acc.posts + s.posts,
      replies: acc.replies + s.replies,
    }),
    { total: 0, comments: 0, posts: 0, replies: 0 }
  ) || { total: 0, comments: 0, posts: 0, replies: 0 };

  const heartbeatMap = new Map(
    (heartbeat.data || []).map((h) => [h.name, h])
  );

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Activity className="h-5 w-5 text-[#06b6d4]" />
            Phantom Activity
          </h2>
          <p className="text-sm text-[#73808c] mt-1">
            Per-persona engagement analytics &middot; <span className="font-mono-data">{personaStats.data?.length || 0}</span> personas tracked
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30].map((d) => (
            <Button key={d} size="sm" variant={days === d ? "default" : "outline"}
              className={days === d ? "bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]" : ""}
              onClick={() => setDays(d)}>
              <span className="font-mono-data text-xs">{d}d</span>
            </Button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {([
          ["Total Actions", totalStats.total, TrendingUp, "#f3f5f7"],
          ["Comments", totalStats.comments, MessageSquare, "#06b6d4"],
          ["Posts", totalStats.posts, FileText, "#22c55e"],
          ["Replies", totalStats.replies, Reply, "#f59e0b"],
        ] as const).map(([label, value, Icon, color]) => (
          <Card key={String(label)}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] text-[#73808c] uppercase tracking-wider font-medium">{String(label)}</p>
                  <p className="text-2xl font-semibold font-mono-data mt-1" style={{ color: String(color) }}>{String(value)}</p>
                </div>
                <div className="h-10 w-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}10` }}>
                  <Icon className="h-5 w-5" style={{ color: String(color) }} />
                </div>
              </div>
              <p className="text-[10px] text-[#73808c] mt-1">Last <span className="font-mono-data">{days}</span> days</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="breakdown">
        <TabsList>
          <TabsTrigger value="breakdown" className="gap-1.5"><BarChart3 className="h-3.5 w-3.5" />Breakdown</TabsTrigger>
          <TabsTrigger value="recent" className="gap-1.5"><Clock className="h-3.5 w-3.5" />Recent Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="breakdown" className="mt-4">
          {personaStats.loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[#73808c]" />
            </div>
          )}

          {personaStats.data && (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
              {personaStats.data
                .sort((a, b) => b.total_actions - a.total_actions)
                .map((stats) => (
                  <PersonaActivityCard
                    key={stats.persona}
                    stats={stats}
                    heartbeat={heartbeatMap.get(stats.persona)}
                    maxActions={maxActions}
                  />
                ))}
            </div>
          )}

          {/* Color Legend */}
          <div className="flex items-center gap-5 text-xs text-[#73808c] pt-3">
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-5 bg-[#06b6d4] rounded-sm" />Comments
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-5 bg-[#22c55e] rounded-sm" />Posts
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-5 bg-[#f59e0b] rounded-sm" />Replies
            </div>
          </div>
        </TabsContent>

        <TabsContent value="recent" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Recent System Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {recentActivity.loading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-[#73808c]" />
                </div>
              )}
              {recentActivity.data && (
                <RecentActivityTable entries={recentActivity.data.entries} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
