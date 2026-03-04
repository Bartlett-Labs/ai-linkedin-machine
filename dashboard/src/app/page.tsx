"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useApi } from "@/hooks/use-api";
import { useAlerts } from "@/hooks/use-alerts";
import { getEngine, getTodaySummary, getWeeklyPlan, updateEngine } from "@/lib/api";
import type { EngineControl, DailySummary, WeeklyPlanDay } from "@/lib/api";
import { Activity, MessageSquare, FileText, Reply, Clock } from "lucide-react";

const MODE_COLORS: Record<string, string> = { Live: "bg-green-500", DryRun: "bg-yellow-500", Paused: "bg-red-500" };

export default function DashboardPage() {
  const engine = useApi<EngineControl>(getEngine);
  const stats = useApi<DailySummary>(getTodaySummary);
  const plan = useApi<WeeklyPlanDay[]>(getWeeklyPlan);
  const alerts = useAlerts();

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>
      {/* Engine Status */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <span>Engine Status</span>
            {engine.data && <Badge className={MODE_COLORS[engine.data.mode] || "bg-gray-500"}>{engine.data.mode}</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {engine.data && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 flex-wrap">
                <span className="text-sm text-muted-foreground">Phase:</span>
                <Badge variant="outline">{engine.data.phase}</Badge>
                <span className="text-sm text-muted-foreground ml-4">Last run:</span>
                <span className="text-sm">{engine.data.last_run || "Never"}</span>
              </div>
              <div className="flex gap-2">
                {(["Live", "DryRun", "Paused"] as const).map((m) => (
                  <Button key={m} size="sm" variant={engine.data?.mode === m ? "default" : "outline"}
                    onClick={() => { updateEngine({ mode: m }).then(() => engine.refetch()); }}>{m}</Button>
                ))}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                {([
                  ["Posting", "main_user_posting"], ["Commenting", "commenting"],
                  ["Replying", "replying"], ["Phantom", "phantom_engagement"],
                ] as const).map(([label, key]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Switch checked={(engine.data as unknown as Record<string, boolean>)[key] ?? false}
                      onCheckedChange={(v) => { updateEngine({ [key]: v } as Partial<EngineControl>).then(() => engine.refetch()); }} />
                    <span className="text-sm">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {engine.loading && <p className="text-sm text-muted-foreground">Loading...</p>}
        </CardContent>
      </Card>
      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {([
          ["Posts Today", stats.data?.posts_made ?? 0, FileText],
          ["Comments", stats.data?.comments_posted ?? 0, MessageSquare],
          ["Replies", stats.data?.replies_sent ?? 0, Reply],
          ["Likes", stats.data?.likes_given ?? 0, Activity],
        ] as const).map(([label, value, Icon]) => (
          <Card key={String(label)}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div><p className="text-sm text-muted-foreground">{String(label)}</p><p className="text-3xl font-bold">{String(value)}</p></div>
                <Icon className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        {/* Schedule */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Clock className="h-5 w-5" />Today&apos;s Schedule</CardTitle></CardHeader>
          <CardContent>
            {plan.data?.[0] && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{plan.data[0].day}, {plan.data[0].date}</p>
                {plan.data[0].is_post_day && <Badge className="bg-blue-500">Post Day</Badge>}
                <div className="space-y-1 mt-2">
                  {plan.data[0].actions.map((action, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm py-1 border-b last:border-0">
                      <Badge variant="outline" className="text-xs">{action.type}</Badge>
                      {action.content_stream && <span>{action.content_stream}</span>}
                      {action.window && <span className="text-muted-foreground">@ {action.window}</span>}
                      {action.target_category && <span>{action.target_category}</span>}
                      {action.count !== undefined && <span className="text-muted-foreground">x{action.count}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        {/* Alerts */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="h-5 w-5" />Engagement Alerts</CardTitle></CardHeader>
          <CardContent>
            {alerts.length === 0 ? <p className="text-sm text-muted-foreground">No pending alerts</p> : (
              <div className="space-y-2">
                {alerts.slice(0, 5).map((a) => (
                  <div key={a.alert_id} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div><p className="text-sm font-medium">{a.commenter_name}</p><p className="text-xs text-muted-foreground truncate max-w-[200px]">{a.comment_text}</p></div>
                    <Badge className={a.urgency === "optimal" ? "bg-green-500" : a.urgency === "good" ? "bg-yellow-500" : a.urgency === "urgent" ? "bg-red-500" : "bg-gray-500"}>
                      {Math.round(a.elapsed_minutes)}m
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
