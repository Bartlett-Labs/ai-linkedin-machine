"use client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { getAlerts, markAlertResponded, dismissAlert } from "@/lib/api";
import type { EngagementAlert } from "@/lib/api";
import { Bell, ExternalLink, Check, X, RefreshCw } from "lucide-react";

const URGENCY: Record<string, string> = { optimal: "#22c55e", good: "#f59e0b", urgent: "#ef4444", missed: "#73808c" };

export default function AlertsPage() {
  const { data: alerts, loading, refetch } = useApi<EngagementAlert[]>(() => getAlerts(50));

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Bell className="h-5 w-5 text-[#f59e0b]" />Engagement Alerts
          </h2>
          <p className="text-sm text-[#73808c] mt-1">Comments on your posts requiring timely responses</p>
        </div>
        <Button variant="outline" size="sm" onClick={refetch} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />Refresh
        </Button>
      </div>
      {loading && <p className="text-[#73808c] text-sm">Loading...</p>}
      {alerts && alerts.length === 0 && (
        <div className="text-center py-12">
          <Bell className="h-8 w-8 mx-auto mb-2 text-[#2a3138]" />
          <p className="text-sm text-[#a7b0b8]">No pending alerts</p>
          <p className="text-xs text-[#73808c] mt-1">All caught up — check back later</p>
        </div>
      )}
      <div className="grid gap-3">
        {alerts?.map((a) => {
          const color = URGENCY[a.urgency] || "#73808c";
          return (
            <Card key={a.alert_id}>
              <CardContent className="pt-5 pb-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <p className="font-medium text-sm">{a.commenter_name}</p>
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full border font-mono-data font-medium"
                        style={{ color, borderColor: `${color}30`, backgroundColor: `${color}10` }}
                      >
                        {a.urgency} · {Math.round(a.elapsed_minutes)}m
                      </span>
                    </div>
                    <p className="text-sm text-[#73808c] mb-2 line-clamp-2">{a.comment_text}</p>
                    {a.post_url && (
                      <a href={a.post_url} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-[#06b6d4] hover:text-[#22d3ee] transition-colors flex items-center gap-1">
                        <ExternalLink className="h-3 w-3" />View on LinkedIn
                      </a>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button size="sm" className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1"
                      onClick={() => { markAlertResponded(a.alert_id).then(refetch); }}>
                      <Check className="h-3.5 w-3.5" />Responded
                    </Button>
                    <Button size="sm" variant="ghost" className="text-[#73808c] hover:text-[#ef4444]"
                      onClick={() => { dismissAlert(a.alert_id).then(refetch); }}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
