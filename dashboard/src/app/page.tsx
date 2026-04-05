"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useApi } from "@/hooks/use-api";
import { useAlerts } from "@/hooks/use-alerts";
import { usePipelineStatus } from "@/hooks/use-pipeline-status";
import { getEngine, getTodaySummary, getWeeklyPlan, updateEngine } from "@/lib/api";
import type { EngineControl, DailySummary, WeeklyPlanDay } from "@/lib/api";
import { Activity, MessageSquare, FileText, Reply, Clock, Play, CheckCircle2, XCircle, Loader2, Wifi, LayoutDashboard } from "lucide-react";

const MODE_STYLES: Record<string, { badge: string; dot: string }> = {
  Live: { badge: "bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/20", dot: "bg-[#22c55e]" },
  DryRun: { badge: "bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20", dot: "bg-[#f59e0b]" },
  Paused: { badge: "bg-[#ef4444]/10 text-[#ef4444] border border-[#ef4444]/20", dot: "bg-[#ef4444]" },
};

export default function DashboardPage() {
  const engine = useApi<EngineControl>(getEngine);
  const stats = useApi<DailySummary>(getTodaySummary);
  const plan = useApi<WeeklyPlanDay[]>(getWeeklyPlan);
  const alerts = useAlerts();
  const pipeline = usePipelineStatus();

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <LayoutDashboard className="h-5 w-5 text-[#06b6d4]" />
          Dashboard
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Operator overview — engine status, pipeline health, daily metrics</p>
      </div>

      {/* Engine Status */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-sm">
            <span className="uppercase tracking-wider text-[11px] font-semibold text-[#73808c]">Engine Status</span>
            {engine.data && (() => {
              const s = MODE_STYLES[engine.data.mode] || MODE_STYLES.Paused;
              return (
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${s.badge}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                  {engine.data.mode}
                </span>
              );
            })()}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {engine.data && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 flex-wrap">
                <span className="text-xs text-[#73808c] uppercase tracking-wider">Phase</span>
                <Badge variant="outline" className="font-mono-data text-xs">{engine.data.phase}</Badge>
                <span className="text-xs text-[#73808c] uppercase tracking-wider ml-4">Last Run</span>
                <span className="text-xs font-mono-data text-[#a7b0b8]">{engine.data.last_run || "Never"}</span>
              </div>
              <div className="flex gap-2">
                {(["Live", "DryRun", "Paused"] as const).map((m) => {
                  const active = engine.data?.mode === m;
                  return (
                    <Button key={m} size="sm"
                      variant={active ? "default" : "outline"}
                      className={active ? "bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]" : ""}
                      onClick={() => { updateEngine({ mode: m }).then(() => engine.refetch()); }}
                    >{m}</Button>
                  );
                })}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                {([
                  ["Posting", "main_user_posting"], ["Commenting", "commenting"],
                  ["Replying", "replying"], ["Phantom", "phantom_engagement"],
                ] as const).map(([label, key]) => (
                  <div key={key} className="flex items-center gap-2.5">
                    <Switch checked={(engine.data as unknown as Record<string, boolean>)[key] ?? false}
                      onCheckedChange={(v) => { updateEngine({ [key]: v } as Partial<EngineControl>).then(() => engine.refetch()); }} />
                    <span className="text-sm text-[#a7b0b8]">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {engine.loading && <p className="text-sm text-[#73808c]">Loading...</p>}
        </CardContent>
      </Card>

      {/* Pipeline Status */}
      {pipeline.connected && (
        <Card className={pipeline.isRunning ? "border-[#06b6d4]/20" : undefined}>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {pipeline.isRunning ? (
                  <>
                    <Loader2 className="h-5 w-5 text-[#06b6d4] animate-spin" />
                    <div>
                      <p className="text-sm font-medium">Pipeline Running — <span className="font-mono-data">Run #{pipeline.activeRun?.id}</span></p>
                      <p className="text-xs text-[#73808c] mt-0.5">
                        <span className="font-mono-data">{pipeline.activeRun?.trigger_type}</span> &middot; {pipeline.activeRun?.phase}
                        {pipeline.liveOutput.length > 0 && (
                          <span className="ml-2 text-[#06b6d4]">{pipeline.liveOutput[pipeline.liveOutput.length - 1]}</span>
                        )}
                      </p>
                    </div>
                  </>
                ) : pipeline.recentRuns.length > 0 ? (
                  <>
                    {pipeline.recentRuns[0].status === "completed" ? (
                      <CheckCircle2 className="h-5 w-5 text-[#22c55e]" />
                    ) : pipeline.recentRuns[0].status === "failed" ? (
                      <XCircle className="h-5 w-5 text-[#ef4444]" />
                    ) : (
                      <Play className="h-5 w-5 text-[#73808c]" />
                    )}
                    <div>
                      <p className="text-sm font-medium">
                        Last Run <span className="font-mono-data">#{pipeline.recentRuns[0].id}</span> — {pipeline.recentRuns[0].status}
                      </p>
                      <p className="text-xs text-[#73808c] mt-0.5">
                        {pipeline.recentRuns[0].summary?.slice(0, 80) || "No summary"}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5 text-[#73808c]" />
                    <p className="text-sm text-[#73808c]">No pipeline runs yet</p>
                  </>
                )}
              </div>
              <span className="inline-flex items-center gap-1 text-[10px] text-[#22c55e]">
                <Wifi className="h-3 w-3" />Live
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {([
          ["Posts Today", stats.data?.posts_made ?? 0, FileText, "#06b6d4"],
          ["Comments", stats.data?.comments_posted ?? 0, MessageSquare, "#22c55e"],
          ["Replies", stats.data?.replies_sent ?? 0, Reply, "#f59e0b"],
          ["Likes", stats.data?.likes_given ?? 0, Activity, "#a7b0b8"],
        ] as const).map(([label, value, Icon, color]) => (
          <Card key={String(label)}>
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[11px] uppercase tracking-wider text-[#73808c] font-medium">{String(label)}</p>
                  <p className="text-3xl font-semibold font-mono-data mt-1">{String(value)}</p>
                </div>
                <div className="h-10 w-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}10` }}>
                  <Icon className="h-5 w-5" style={{ color: String(color) }} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Schedule */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-[#06b6d4]" />
              Today&apos;s Schedule
            </CardTitle>
          </CardHeader>
          <CardContent>
            {plan.data?.[0] && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <p className="text-sm text-[#a7b0b8]">{plan.data[0].day}, <span className="font-mono-data">{plan.data[0].date}</span></p>
                  {plan.data[0].is_post_day && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#06b6d4]/10 text-[#06b6d4] border border-[#06b6d4]/20 font-medium">
                      Post Day
                    </span>
                  )}
                </div>
                <div className="space-y-0.5 mt-2">
                  {plan.data[0].actions.map((action, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm py-1.5 border-b border-[#2a3138]/50 last:border-0">
                      <Badge variant="outline" className="text-[10px] font-mono-data">{action.type}</Badge>
                      {action.content_stream && <span className="text-[#a7b0b8]">{action.content_stream}</span>}
                      {action.window && <span className="text-[#73808c] font-mono-data text-xs">@ {action.window}</span>}
                      {action.target_category && <span className="text-[#a7b0b8]">{action.target_category}</span>}
                      {action.count !== undefined && <span className="text-[#73808c] font-mono-data">x{action.count}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-[#f59e0b]" />
              Engagement Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <p className="text-sm text-[#73808c]">No pending alerts</p>
            ) : (
              <div className="space-y-1">
                {alerts.slice(0, 5).map((a) => {
                  const urgencyColor = a.urgency === "optimal" ? "#22c55e" : a.urgency === "good" ? "#f59e0b" : a.urgency === "urgent" ? "#ef4444" : "#73808c";
                  return (
                    <div key={a.alert_id} className="flex items-center justify-between py-2 border-b border-[#2a3138]/50 last:border-0">
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{a.commenter_name}</p>
                        <p className="text-xs text-[#73808c] truncate max-w-[220px]">{a.comment_text}</p>
                      </div>
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full border font-mono-data font-medium shrink-0 ml-2"
                        style={{ color: urgencyColor, borderColor: `${urgencyColor}30`, backgroundColor: `${urgencyColor}10` }}
                      >
                        {Math.round(a.elapsed_minutes)}m
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
