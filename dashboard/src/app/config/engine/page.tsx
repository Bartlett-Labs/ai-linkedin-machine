"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { getEngine, updateEngine } from "@/lib/api";
import type { EngineControl } from "@/lib/api";
import { Zap } from "lucide-react";

export default function EngineConfigPage() {
  const { data, loading, refetch } = useApi<EngineControl>(getEngine);
  const update = (patch: Partial<EngineControl>) => updateEngine(patch).then(refetch);

  if (loading || !data) return <p className="text-muted-foreground">Loading...</p>;
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2"><Zap className="h-6 w-6" />Engine Configuration</h2>
      <Card>
        <CardHeader><CardTitle>Mode & Phase</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-sm w-20">Mode:</span>
            <Select value={data.mode} onValueChange={(v) => update({ mode: v })}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="Live">Live</SelectItem><SelectItem value="DryRun">DryRun</SelectItem><SelectItem value="Paused">Paused</SelectItem></SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm w-20">Phase:</span>
            <Select value={data.phase} onValueChange={(v) => update({ phase: v })}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="stealth">Stealth</SelectItem><SelectItem value="announcement">Announcement</SelectItem><SelectItem value="authority">Authority</SelectItem></SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Feature Toggles</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {([["Main User Posting", "main_user_posting"], ["Commenting", "commenting"], ["Replying", "replying"], ["Phantom Engagement", "phantom_engagement"]] as const).map(([label, key]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm">{label}</span>
              <Switch checked={(data as unknown as Record<string, boolean>)[key]} onCheckedChange={(v) => update({ [key]: v } as Partial<EngineControl>)} />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
