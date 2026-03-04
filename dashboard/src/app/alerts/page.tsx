"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useApi } from "@/hooks/use-api";
import { getAlerts, markAlertResponded, dismissAlert } from "@/lib/api";
import type { EngagementAlert } from "@/lib/api";
import { Bell, ExternalLink, Check, X } from "lucide-react";

const URGENCY_COLORS: Record<string, string> = { optimal: "bg-green-500", good: "bg-yellow-500", urgent: "bg-red-500", missed: "bg-gray-500" };

export default function AlertsPage() {
  const { data: alerts, loading, refetch } = useApi<EngagementAlert[]>(() => getAlerts(50));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Bell className="h-6 w-6" />Engagement Alerts</h2>
        <Button variant="outline" size="sm" onClick={refetch}>Refresh</Button>
      </div>
      {loading && <p className="text-muted-foreground">Loading...</p>}
      {alerts && alerts.length === 0 && <p className="text-muted-foreground">No pending alerts. All caught up!</p>}
      <div className="grid gap-4">
        {alerts?.map((a) => (
          <Card key={a.alert_id}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium">{a.commenter_name}</p>
                    <Badge className={URGENCY_COLORS[a.urgency]}>{a.urgency} ({Math.round(a.elapsed_minutes)}m)</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2 line-clamp-2">{a.comment_text}</p>
                  {a.post_url && (
                    <a href={a.post_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:underline flex items-center gap-1">
                      <ExternalLink className="h-3 w-3" />View on LinkedIn
                    </a>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="default" onClick={() => { markAlertResponded(a.alert_id).then(refetch); }}>
                    <Check className="h-4 w-4 mr-1" />Responded
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { dismissAlert(a.alert_id).then(refetch); }}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
