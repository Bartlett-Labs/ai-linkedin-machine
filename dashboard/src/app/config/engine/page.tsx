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

  if (loading || !data) return <p className="text-[#73808c] text-sm">Loading...</p>;
  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <Zap className="h-5 w-5 text-[#06b6d4]" />Engine Configuration
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Core engine mode, phase, and feature toggles</p>
      </div>
      <Card>
        <CardHeader><CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Mode & Phase</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-sm text-[#a7b0b8] w-20">Mode:</span>
            <Select value={data.mode} onValueChange={(v) => update({ mode: v })}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="Live">Live</SelectItem><SelectItem value="DryRun">DryRun</SelectItem><SelectItem value="Paused">Paused</SelectItem></SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[#a7b0b8] w-20">Phase:</span>
            <Select value={data.phase} onValueChange={(v) => update({ phase: v })}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="stealth">Stealth</SelectItem><SelectItem value="announcement">Announcement</SelectItem><SelectItem value="authority">Authority</SelectItem></SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Feature Toggles</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {([["Main User Posting", "main_user_posting"], ["Commenting", "commenting"], ["Replying", "replying"], ["Phantom Engagement", "phantom_engagement"]] as const).map(([label, key]) => (
            <div key={key} className="flex items-center justify-between py-1">
              <span className="text-sm text-[#a7b0b8]">{label}</span>
              <Switch checked={(data as unknown as Record<string, boolean>)[key]} onCheckedChange={(v) => update({ [key]: v } as Partial<EngineControl>)} />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
