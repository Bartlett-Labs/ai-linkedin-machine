"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getPipelineRuns, triggerPipelineRun, type PipelineRun } from "@/lib/api";
import { usePipelineStatus } from "@/hooks/use-pipeline-status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Play, RefreshCw, Clock, CheckCircle2, XCircle,
  Loader2, MessageSquare, Send, Ghost, Heart,
  ChevronDown, ChevronUp, Zap, Activity, Terminal, Wifi, WifiOff,
} from "lucide-react";

const RUN_STATUS: Record<string, { label: string; color: string; bg: string; border: string; icon: typeof CheckCircle2 }> = {
  running:   { label: "Running",   color: "text-[#06b6d4]",   bg: "bg-[#06b6d4]/10",   border: "border-[#06b6d4]/30",   icon: Loader2 },
  completed: { label: "Completed", color: "text-[#22c55e]",   bg: "bg-[#22c55e]/10",   border: "border-[#22c55e]/30",   icon: CheckCircle2 },
  failed:    { label: "Failed",    color: "text-[#ef4444]",   bg: "bg-[#ef4444]/10",   border: "border-[#ef4444]/30",   icon: XCircle },
  pending:   { label: "Pending",   color: "text-[#f59e0b]",   bg: "bg-[#f59e0b]/10",   border: "border-[#f59e0b]/30",   icon: Clock },
};

function RunStatusBadge({ status }: { status: string }) {
  const cfg = RUN_STATUS[status] || RUN_STATUS.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full border ${cfg.color} ${cfg.bg} ${cfg.border}`}>
      <Icon className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`} />
      {cfg.label}
    </span>
  );
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "\u2014";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.round((e - s) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`;
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`;
}

function formatDate(iso: string | null) {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

function StatPill({ icon: Icon, value, label, color }: { icon: typeof Send; value: number; label: string; color: string }) {
  if (value === 0) return null;
  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-[#111315] text-xs" style={{ color }}>
      <Icon className="h-3 w-3" />
      <span className="font-mono-data font-medium">{value}</span>
      <span className="text-[#73808c]">{label}</span>
    </div>
  );
}

function LiveOutputConsole({ lines }: { lines: string[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  if (lines.length === 0) return null;
  return (
    <div className="rounded-[10px] border border-[#06b6d4]/20 bg-[#090a0b] overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#06b6d4]/10 bg-[#06b6d4]/5">
        <Terminal className="h-3.5 w-3.5 text-[#06b6d4]" />
        <span className="text-xs font-medium text-[#06b6d4]">Live Output</span>
        <span className="text-[10px] text-[#73808c] ml-auto font-mono-data">{lines.length} lines</span>
      </div>
      <div className="max-h-64 overflow-y-auto p-3 font-mono-data text-xs leading-relaxed text-[#22c55e]/80">
        {lines.map((line, i) => (
          <div key={i} className={line.includes("ERROR") || line.includes("FAIL") ? "text-[#ef4444]" : line.includes("WARN") ? "text-[#f59e0b]" : ""}>
            {line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

export default function PipelineRunsPage() {
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggerOpen, setTriggerOpen] = useState(false);
  const [dryRun, setDryRun] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [expandedRun, setExpandedRun] = useState<number | null>(null);
  const [lastTriggered, setLastTriggered] = useState<{ run_id: number; phase: string } | null>(null);

  const pipeline = usePipelineStatus();

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getPipelineRuns({ limit: 50 });
      setRuns(res.runs);
    } catch (e) {
      console.error("Failed to fetch runs:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  useEffect(() => {
    if (pipeline.recentRuns.length > 0) {
      setRuns(prev => {
        const wsIds = new Set(pipeline.recentRuns.map(r => r.id));
        const older = prev.filter(r => !wsIds.has(r.id));
        return [...pipeline.recentRuns, ...older].sort((a, b) => b.id - a.id);
      });
    }
  }, [pipeline.recentRuns]);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      const result = await triggerPipelineRun({ trigger_type: "manual", dry_run: dryRun });
      setLastTriggered({ run_id: result.run_id, phase: result.phase });
      setTriggerOpen(false);
      fetchRuns();
    } catch (e) {
      console.error("Failed to trigger run:", e);
    } finally {
      setTriggering(false);
    }
  };

  const activeRun = pipeline.activeRun || runs.find(r => r.status === "running");
  const completedCount = runs.filter(r => r.status === "completed").length;
  const failedCount = runs.filter(r => r.status === "failed").length;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Activity className="h-5 w-5 text-[#06b6d4]" />
            Pipeline Runs
          </h2>
          <p className="text-sm text-[#73808c] mt-1">Trigger, monitor, and review pipeline execution history</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] border ${pipeline.connected ? "text-[#22c55e] border-[#22c55e]/30 bg-[#22c55e]/5" : "text-[#73808c] border-[#2a3138]"}`}>
            {pipeline.connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {pipeline.connected ? "Live" : "Offline"}
          </span>
          <Button variant="outline" size="sm" onClick={fetchRuns} disabled={loading} className="gap-1.5">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />Refresh
          </Button>
          <Dialog open={triggerOpen} onOpenChange={setTriggerOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5">
                <Play className="h-3.5 w-3.5" />Run Now
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-sm">
              <DialogHeader><DialogTitle>Trigger Pipeline Run</DialogTitle></DialogHeader>
              <div className="space-y-5 pt-2">
                <div className="rounded-lg border border-[#f59e0b]/20 bg-[#f59e0b]/5 p-3">
                  <p className="text-xs text-[#f59e0b]">This will execute the full pipeline: ingest, generate, post, comment, reply. The engine&apos;s current mode and phase settings will be used.</p>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Dry Run</Label>
                    <p className="text-xs text-[#73808c]">Simulate without posting to LinkedIn</p>
                  </div>
                  <Switch checked={dryRun} onCheckedChange={setDryRun} />
                </div>
                <Button onClick={handleTrigger} className="w-full bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]" disabled={triggering}>
                  {triggering ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Zap className="h-4 w-4 mr-1.5" />}
                  {triggering ? "Starting..." : dryRun ? "Start Dry Run" : "Start Pipeline"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-4 gap-3">
        <div className={`rounded-[10px] border p-3 ${activeRun ? "border-[#06b6d4]/30 bg-[#06b6d4]/5" : "border-[#2a3138]"}`}>
          <div className="flex items-center justify-between">
            <Activity className={`h-4 w-4 ${activeRun ? "text-[#06b6d4]" : "text-[#73808c]"}`} />
            {activeRun ? (
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#06b6d4] opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#06b6d4]" />
              </span>
            ) : (
              <span className="text-xs text-[#73808c]">idle</span>
            )}
          </div>
          <p className="text-xs text-[#73808c] mt-2">{activeRun ? "Running" : "Status"}</p>
          <p className="text-sm font-medium mt-0.5">{activeRun ? <><span className="font-mono-data">Run #{activeRun.id}</span> &mdash; {formatDuration(activeRun.started_at, null)}</> : "No active run"}</p>
        </div>
        <div className="rounded-[10px] border border-[#2a3138] p-3">
          <p className="text-2xl font-semibold font-mono-data">{runs.length}</p>
          <p className="text-xs text-[#73808c] mt-1">Total Runs</p>
        </div>
        <div className="rounded-[10px] border border-[#2a3138] p-3">
          <p className="text-2xl font-semibold font-mono-data text-[#22c55e]">{completedCount}</p>
          <p className="text-xs text-[#73808c] mt-1">Completed</p>
        </div>
        <div className="rounded-[10px] border border-[#2a3138] p-3">
          <p className="text-2xl font-semibold font-mono-data text-[#ef4444]">{failedCount}</p>
          <p className="text-xs text-[#73808c] mt-1">Failed</p>
        </div>
      </div>

      {/* Live Output Console */}
      {pipeline.isRunning && <LiveOutputConsole lines={pipeline.liveOutput} />}

      {/* Last triggered banner */}
      {lastTriggered && (
        <div className="rounded-lg border border-[#22c55e]/20 bg-[#22c55e]/5 p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-[#22c55e]" />
            <span className="text-sm">Pipeline run <span className="font-mono-data font-medium">#{lastTriggered.run_id}</span> triggered successfully</span>
            <Badge variant="outline" className="text-[10px] font-mono-data">{lastTriggered.phase}</Badge>
          </div>
          <Button variant="ghost" size="sm" className="text-xs" onClick={() => setLastTriggered(null)}>Dismiss</Button>
        </div>
      )}

      {/* Run History */}
      <div className="space-y-2">
        {loading && runs.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-[#73808c]">Loading runs...</CardContent></Card>
        ) : runs.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <Play className="h-8 w-8 text-[#2a3138] mx-auto mb-3" />
              <p className="text-sm text-[#a7b0b8]">No pipeline runs yet</p>
              <p className="text-xs text-[#73808c] mt-1">Click &ldquo;Run Now&rdquo; to trigger your first pipeline execution</p>
            </CardContent>
          </Card>
        ) : (
          runs.map(run => {
            const expanded = expandedRun === run.id;
            const totalActions = run.posts_made + run.comments_made + run.replies_made + run.phantom_actions;
            return (
              <Card key={run.id} className={`transition-colors ${run.status === "running" ? "border-[#06b6d4]/20" : "hover:border-[#f3f5f7]/15"}`}>
                <CardContent className="py-4">
                  <button className="w-full text-left" onClick={() => setExpandedRun(expanded ? null : run.id)}>
                    <div className="flex items-center gap-4">
                      <div className="w-20 flex-shrink-0">
                        <span className="text-sm font-mono-data font-medium text-[#73808c]">#{run.id}</span>
                      </div>
                      <RunStatusBadge status={run.status} />
                      <Badge variant="outline" className="text-[10px] font-mono-data">{run.phase || "\u2014"}</Badge>
                      <Badge variant="outline" className="text-[10px]">{run.trigger_type}</Badge>

                      <div className="flex-1 flex items-center gap-2">
                        {totalActions > 0 && (
                          <span className="text-xs text-[#73808c]"><span className="font-mono-data">{totalActions}</span> action{totalActions !== 1 ? "s" : ""}</span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 text-xs text-[#73808c]">
                        <span className="font-mono-data">{formatDuration(run.started_at, run.completed_at)}</span>
                        <span className="font-mono-data">{formatDate(run.started_at)}</span>
                        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </div>
                    </div>
                  </button>

                  {expanded && (
                    <div className="mt-4 pt-4 border-t border-[#2a3138]/50 space-y-3">
                      {/* Action Stats */}
                      <div className="flex flex-wrap gap-2">
                        <StatPill icon={Send} value={run.posts_made} label="posts" color="#22c55e" />
                        <StatPill icon={MessageSquare} value={run.comments_made} label="comments" color="#06b6d4" />
                        <StatPill icon={MessageSquare} value={run.replies_made} label="replies" color="#f59e0b" />
                        <StatPill icon={Ghost} value={run.phantom_actions} label="phantom" color="#a7b0b8" />
                      </div>

                      {/* Timestamps */}
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-[#73808c]">Started:</span>
                          <span className="ml-2 font-mono-data">{formatDate(run.started_at)}</span>
                        </div>
                        <div>
                          <span className="text-[#73808c]">Completed:</span>
                          <span className="ml-2 font-mono-data">{formatDate(run.completed_at)}</span>
                        </div>
                      </div>

                      {/* Summary */}
                      {run.summary && (
                        <div className="rounded-lg bg-[#111315] p-3">
                          <p className="text-xs text-[#73808c] mb-1">Summary</p>
                          <p className="text-sm">{run.summary}</p>
                        </div>
                      )}

                      {/* Errors */}
                      {run.errors && Object.keys(run.errors).length > 0 && (
                        <div className="rounded-lg bg-[#ef4444]/5 border border-[#ef4444]/20 p-3">
                          <p className="text-xs text-[#ef4444] mb-1">Errors</p>
                          <pre className="text-xs font-mono-data text-[#ef4444]/80 whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(run.errors, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
