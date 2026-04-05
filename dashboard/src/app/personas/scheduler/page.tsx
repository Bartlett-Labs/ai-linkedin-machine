"use client";
import { useCallback, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useApi } from "@/hooks/use-api";
import {
  getHeartbeatStatus,
  getKillSwitch,
  activateKillSwitch,
  deactivateKillSwitch,
  triggerHeartbeat,
  triggerAllHeartbeats,
  updatePersonaSchedule,
} from "@/lib/api";
import type { PersonaHeartbeatStatus, KillSwitchStatus, ScheduleUpdate } from "@/lib/api";
import {
  HeartPulse,
  Play,
  Pause,
  Settings2,
  Wifi,
  WifiOff,
  Clock,
  Clock3,
  MessageSquare,
  FileText,
  Zap,
  ShieldAlert,
  ShieldCheck,
  User,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";

// Persona-specific accent colors for visual distinction
const PERSONA_COLORS: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  "The Visionary Advisor":           { bg: "bg-[#06b6d4]/8",  border: "border-[#06b6d4]/20",  text: "text-[#06b6d4]",  glow: "" },
  "The Deep Learner":                { bg: "bg-[#2dd4bf]/8",  border: "border-[#2dd4bf]/20",  text: "text-[#2dd4bf]",  glow: "" },
  "The Skeptical Senior Dev":        { bg: "bg-[#f59e0b]/8",  border: "border-[#f59e0b]/20",  text: "text-[#f59e0b]",  glow: "" },
  "The Corporate Compliance Officer":{ bg: "bg-[#a7b0b8]/8",  border: "border-[#a7b0b8]/20",  text: "text-[#a7b0b8]",  glow: "" },
  "The Creative Tinkerer":           { bg: "bg-[#22c55e]/8",  border: "border-[#22c55e]/20",  text: "text-[#22c55e]",  glow: "" },
  "The ROI-Driven Manager":          { bg: "bg-[#fb923c]/8",  border: "border-[#fb923c]/20",  text: "text-[#fb923c]",  glow: "" },
};

const DEFAULT_COLOR = { bg: "bg-[#1b2024]", border: "border-[#2a3138]", text: "text-[#f3f5f7]", glow: "" };

function StatusDot({ status }: { status: "active" | "inactive" | "outside-hours" | "running" }) {
  const styles = {
    active: "bg-[#22c55e] shadow-[0_0_6px_#22c55e80]",
    inactive: "bg-[#ef4444]/70",
    "outside-hours": "bg-[#f59e0b]/70",
    running: "bg-[#06b6d4] shadow-[0_0_6px_#06b6d480] animate-pulse",
  };
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${styles[status]}`} />;
}

function StatBlock({ label, value, max, icon: Icon }: { label: string; value: number; max?: number; icon: React.ComponentType<{ className?: string }> }) {
  const pct = max && max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const barColor = pct >= 90 ? "bg-[#ef4444]" : pct >= 60 ? "bg-[#f59e0b]" : "bg-[#06b6d4]";
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-[#73808c] uppercase tracking-wider flex items-center gap-1">
          <Icon className="h-3 w-3" />{label}
        </span>
        <span className="text-sm font-mono-data font-medium">
          {value}{max !== undefined ? <span className="text-[#73808c]">/{max}</span> : null}
        </span>
      </div>
      {max !== undefined && max > 0 && (
        <div className="h-1 bg-[#1b2024] rounded-full overflow-hidden">
          <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

function ScheduleEditDialog({
  persona,
  open,
  onClose,
  onSaved,
}: {
  persona: PersonaHeartbeatStatus;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const s = persona.schedule || {};
  const [commentsPerCycle, setCommentsPerCycle] = useState(s.comments_per_cycle ?? 2);
  const [postChance, setPostChance] = useState(s.post_chance_per_cycle ?? 0.1);
  const [kyleChance, setKyleChance] = useState(s.kyle_comment_chance ?? 0.2);
  const [interval, setInterval] = useState(s.cycle_interval_minutes ?? 60);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    const data: ScheduleUpdate = {
      comments_per_cycle: commentsPerCycle,
      post_chance_per_cycle: postChance,
      kyle_comment_chance: kyleChance,
      cycle_interval_minutes: interval,
    };
    await updatePersonaSchedule(persona.name, data);
    setSaving(false);
    onSaved();
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Schedule: {persona.display_name}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-5 pt-2">
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider">Comments per Cycle</Label>
            <Input type="number" min={0} max={10} value={commentsPerCycle}
              onChange={(e) => setCommentsPerCycle(Number(e.target.value))} className="mt-1 font-mono-data" />
            <p className="text-[11px] text-muted-foreground mt-1">Feed comments posted each heartbeat cycle</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider">Post Chance (%)</Label>
            <Input type="number" min={0} max={100} step={5} value={Math.round(postChance * 100)}
              onChange={(e) => setPostChance(Number(e.target.value) / 100)} className="mt-1 font-mono-data" />
            <p className="text-[11px] text-muted-foreground mt-1">Probability of generating + publishing a post each cycle</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider">Kyle Comment Chance (%)</Label>
            <Input type="number" min={0} max={100} step={5} value={Math.round(kyleChance * 100)}
              onChange={(e) => setKyleChance(Number(e.target.value) / 100)} className="mt-1 font-mono-data" />
            <p className="text-[11px] text-muted-foreground mt-1">Probability of commenting on Kyle's posts each cycle</p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground uppercase tracking-wider">Cycle Interval (minutes)</Label>
            <Input type="number" min={15} max={480} step={15} value={interval}
              onChange={(e) => setInterval(Number(e.target.value))} className="mt-1 font-mono-data" />
            <p className="text-[11px] text-muted-foreground mt-1">How often the heartbeat fires</p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={save} disabled={saving}>{saving ? "Saving..." : "Update Schedule"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function PersonaCard({
  persona,
  onRefresh,
}: {
  persona: PersonaHeartbeatStatus;
  onRefresh: () => void;
}) {
  const [editOpen, setEditOpen] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState<"success" | "error" | null>(null);

  const colors = PERSONA_COLORS[persona.name] || DEFAULT_COLOR;
  const schedule = persona.schedule || {};
  const stats = persona.daily_stats || { comments_posted: 0, posts_made: 0, replies_sent: 0, likes_given: 0 };
  const behavior = {} as Record<string, number>; // behavior comes from schedule config
  const commentLimit = schedule.comments_per_cycle ? schedule.comments_per_cycle * Math.floor(12 / (schedule.cycle_interval_minutes || 60) * 60) : 5;

  const getStatus = (): "active" | "inactive" | "outside-hours" | "running" => {
    if (persona.is_running) return "running";
    if (!persona.has_active_session) return "inactive";
    if (!persona.in_active_hours) return "outside-hours";
    return "active";
  };

  const statusLabel: Record<string, string> = {
    active: "Ready",
    inactive: "No Session",
    "outside-hours": "Off-Hours",
    running: "Running",
  };

  const status = getStatus();

  const handleTrigger = async (dryRun: boolean) => {
    setTriggering(true);
    setTriggerResult(null);
    try {
      await triggerHeartbeat(persona.name, { dry_run: dryRun });
      setTriggerResult("success");
      setTimeout(() => { setTriggerResult(null); onRefresh(); }, 2000);
    } catch {
      setTriggerResult("error");
      setTimeout(() => setTriggerResult(null), 3000);
    }
    setTriggering(false);
  };

  const activeHoursStr = persona.active_hours
    ? `${persona.active_hours.start} - ${persona.active_hours.end} ${persona.active_hours.timezone?.split("/").pop() || ""}`
    : "Always";

  return (
    <>
      <Card className={`${colors.bg} ${colors.border} border transition-all hover:shadow-lg ${colors.glow} relative overflow-hidden`}>
        {/* Subtle gradient accent at top */}
        <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent ${colors.text.replace("text-", "via-")} to-transparent opacity-50`} />

        <CardContent className="pt-5 pb-4 space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-lg ${colors.bg} border ${colors.border} flex items-center justify-center`}>
                <User className={`h-5 w-5 ${colors.text}`} />
              </div>
              <div>
                <h3 className="font-semibold text-sm">{persona.display_name}</h3>
                <p className="text-[11px] text-muted-foreground">{persona.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusDot status={status} />
              <Badge variant="outline" className={`text-[10px] font-mono-data ${
                status === "active" ? "border-[#22c55e]/30 text-[#22c55e]" :
                status === "running" ? "border-[#06b6d4]/30 text-[#06b6d4]" :
                status === "inactive" ? "border-[#ef4444]/30 text-[#ef4444]" :
                "border-[#f59e0b]/30 text-[#f59e0b]"
              }`}>
                {statusLabel[status]}
              </Badge>
            </div>
          </div>

          {/* Schedule Info */}
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="space-y-0.5">
              <span className="text-muted-foreground flex items-center gap-1"><Clock className="h-3 w-3" />Window</span>
              <span className="font-mono-data text-[11px]">{activeHoursStr}</span>
            </div>
            <div className="space-y-0.5">
              <span className="text-muted-foreground flex items-center gap-1"><Clock3 className="h-3 w-3" />Interval</span>
              <span className="font-mono-data text-[11px]">{schedule.cycle_interval_minutes || 60}m</span>
            </div>
            <div className="space-y-0.5">
              <span className="text-muted-foreground flex items-center gap-1"><Zap className="h-3 w-3" />Per Cycle</span>
              <span className="font-mono-data text-[11px]">{schedule.comments_per_cycle ?? 2} comments</span>
            </div>
          </div>

          {/* Probability bars */}
          <div className="grid grid-cols-2 gap-4 p-3 rounded-lg bg-[#090a0b]/40 border border-[#2a3138]/50">
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Post Chance</span>
                <span className="text-xs font-mono-data font-medium">{Math.round((schedule.post_chance_per_cycle ?? 0.1) * 100)}%</span>
              </div>
              <div className="h-1.5 bg-[#1b2024] rounded-full overflow-hidden">
                <div className="h-full bg-[#06b6d4]/70 rounded-full" style={{ width: `${(schedule.post_chance_per_cycle ?? 0.1) * 100}%` }} />
              </div>
            </div>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Kyle Chance</span>
                <span className="text-xs font-mono-data font-medium">{Math.round((schedule.kyle_comment_chance ?? 0.2) * 100)}%</span>
              </div>
              <div className="h-1.5 bg-[#1b2024] rounded-full overflow-hidden">
                <div className="h-full bg-[#22c55e]/70 rounded-full" style={{ width: `${(schedule.kyle_comment_chance ?? 0.2) * 100}%` }} />
              </div>
            </div>
          </div>

          {/* Daily Stats */}
          <div className="grid grid-cols-2 gap-3">
            <StatBlock label="Comments" value={stats.comments_posted} max={commentLimit} icon={MessageSquare} />
            <StatBlock label="Posts" value={stats.posts_made} max={1} icon={FileText} />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm" variant="outline"
                    className="flex-1 gap-1.5 text-xs"
                    disabled={!persona.has_active_session || triggering || persona.is_running}
                    onClick={() => handleTrigger(false)}
                  >
                    {triggering ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> :
                     triggerResult === "success" ? <CheckCircle2 className="h-3.5 w-3.5 text-[#22c55e]" /> :
                     triggerResult === "error" ? <XCircle className="h-3.5 w-3.5 text-[#ef4444]" /> :
                     <Play className="h-3.5 w-3.5" />}
                    {triggering ? "Running..." : triggerResult === "success" ? "Triggered" : triggerResult === "error" ? "Failed" : "Run Heartbeat"}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {!persona.has_active_session ? "No active browser session — login required" : "Run one heartbeat cycle (live)"}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm" variant="ghost"
                    className="text-xs text-muted-foreground"
                    disabled={!persona.has_active_session || triggering}
                    onClick={() => handleTrigger(true)}
                  >
                    Dry Run
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Generate but don't post (test mode)</TooltipContent>
              </Tooltip>
            </TooltipProvider>

            <Button size="sm" variant="ghost" className="ml-auto" onClick={() => setEditOpen(true)}>
              <Settings2 className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      <ScheduleEditDialog
        persona={persona}
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSaved={onRefresh}
      />
    </>
  );
}

export default function PersonaSchedulerPage() {
  const heartbeat = useApi<PersonaHeartbeatStatus[]>(getHeartbeatStatus);
  const killSwitch = useApi<KillSwitchStatus>(getKillSwitch);
  const [runAllLoading, setRunAllLoading] = useState(false);

  const handleRunAll = async (dryRun: boolean) => {
    setRunAllLoading(true);
    try {
      await triggerAllHeartbeats({ dry_run: dryRun });
      setTimeout(() => heartbeat.refetch(), 2000);
    } catch (e) {
      console.error("Run all failed:", e);
    }
    setRunAllLoading(false);
  };

  const handleKillSwitch = async () => {
    if (killSwitch.data?.active) {
      await deactivateKillSwitch();
    } else {
      await activateKillSwitch();
    }
    killSwitch.refetch();
    heartbeat.refetch();
  };

  const activeCount = heartbeat.data?.filter((p) => p.has_active_session && p.in_active_hours).length ?? 0;
  const sessionCount = heartbeat.data?.filter((p) => p.has_active_session).length ?? 0;
  const totalCount = heartbeat.data?.length ?? 0;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <HeartPulse className="h-5 w-5 text-[#06b6d4]" />
            Persona Scheduler
          </h2>
          <p className="text-sm text-[#73808c] mt-1">
            Per-persona autonomous heartbeat control &middot;{" "}
            <span className="font-mono-data">{activeCount}</span> active &middot;{" "}
            <span className="font-mono-data">{sessionCount}/{totalCount}</span> sessions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => handleRunAll(true)} disabled={runAllLoading}>
            Dry Run All
          </Button>
          <Button size="sm" onClick={() => handleRunAll(false)} disabled={runAllLoading || killSwitch.data?.active}
            className="gap-1.5 bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">
            {runAllLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run All Eligible
          </Button>
        </div>
      </div>

      {/* Kill Switch Banner */}
      <Card className={`border transition-colors ${
        killSwitch.data?.active
          ? "border-[#ef4444]/40 bg-[#ef4444]/5"
          : "border-[#22c55e]/20 bg-[#22c55e]/[0.03]"
      }`}>
        <CardContent className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {killSwitch.data?.active ? (
                <ShieldAlert className="h-5 w-5 text-[#ef4444]" />
              ) : (
                <ShieldCheck className="h-5 w-5 text-[#22c55e]" />
              )}
              <div>
                <p className="text-sm font-medium">
                  {killSwitch.data?.active ? "KILL SWITCH ACTIVE" : "Systems Operational"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {killSwitch.data?.active
                    ? "All automation halted — heartbeats, commenting, posting, replying"
                    : "All automation systems running normally"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">Kill Switch</span>
              <Switch
                checked={killSwitch.data?.active ?? false}
                onCheckedChange={handleKillSwitch}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {heartbeat.loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Error State */}
      {heartbeat.error && (
        <Card className="border-[#ef4444]/30 bg-[#ef4444]/5">
          <CardContent className="py-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-[#ef4444]" />
              <p className="text-sm text-[#ef4444]">Failed to load heartbeat status: {heartbeat.error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Persona Grid */}
      {heartbeat.data && (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {heartbeat.data.map((persona) => (
            <PersonaCard key={persona.name} persona={persona} onRefresh={heartbeat.refetch} />
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-6 text-xs text-muted-foreground pt-2">
        <div className="flex items-center gap-1.5"><StatusDot status="active" />Ready (session + in hours)</div>
        <div className="flex items-center gap-1.5"><StatusDot status="running" />Running heartbeat</div>
        <div className="flex items-center gap-1.5"><StatusDot status="outside-hours" />Outside active hours</div>
        <div className="flex items-center gap-1.5"><StatusDot status="inactive" />No browser session</div>
      </div>
    </div>
  );
}
