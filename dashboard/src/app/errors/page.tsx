"use client";

import { useState, useEffect, useCallback } from "react";
import { getPipelineErrors, type PipelineError, type ErrorsResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertTriangle, RefreshCw, XCircle, Activity,
  ChevronDown, ChevronUp, Server, ScrollText, ShieldAlert,
} from "lucide-react";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  const min = Math.floor(ms / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function SeverityIndicator({ result }: { result?: string }) {
  const text = (result || "").toLowerCase();
  const isCritical = text.includes("challenge") || text.includes("captcha") || text.includes("blocked");
  const isError = text.includes("fail") || text.includes("error") || text.includes("exception");

  if (isCritical) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
        </span>
        <span className="text-[10px] font-medium text-red-400 uppercase tracking-wider">Critical</span>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="flex items-center gap-1.5">
        <span className="inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
        <span className="text-[10px] font-medium text-amber-400 uppercase tracking-wider">Error</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5">
      <span className="inline-flex rounded-full h-2.5 w-2.5 bg-zinc-500" />
      <span className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider">Warning</span>
    </div>
  );
}

export default function ErrorsPage() {
  const [data, setData] = useState<ErrorsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [tab, setTab] = useState("all");

  const fetchErrors = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getPipelineErrors({ limit: 200 });
      setData(res);
    } catch (e) {
      console.error("Failed to fetch errors:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchErrors(); }, [fetchErrors]);

  const toggleExpand = (key: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const pipelineErrors = data?.pipeline_errors || [];
  const systemErrors = data?.system_errors || [];
  const totalErrors = (data?.pipeline_error_count || 0) + (data?.system_error_count || 0);

  // Group system errors by module
  const moduleGroups = systemErrors.reduce<Record<string, PipelineError[]>>((acc, err) => {
    const mod = err.module || "unknown";
    (acc[mod] = acc[mod] || []).push(err);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Error Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">Aggregated errors from pipeline runs and system logs</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchErrors} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />Refresh
        </Button>
      </div>

      {/* Error Summary Strip */}
      <div className="grid grid-cols-3 gap-3">
        <div className={`rounded-lg border p-4 ${totalErrors > 0 ? "border-red-500/20 bg-red-500/5" : "border-border"}`}>
          <div className="flex items-center justify-between">
            <AlertTriangle className={`h-5 w-5 ${totalErrors > 0 ? "text-red-400" : "text-muted-foreground"}`} />
            <span className={`text-3xl font-bold tabular-nums ${totalErrors > 0 ? "text-red-400" : "text-muted-foreground"}`}>{totalErrors}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Total Errors</p>
        </div>
        <div className="rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <Activity className="h-5 w-5 text-amber-400" />
            <span className="text-3xl font-bold tabular-nums text-amber-400">{data?.pipeline_error_count || 0}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Pipeline Failures</p>
        </div>
        <div className="rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <Server className="h-5 w-5 text-purple-400" />
            <span className="text-3xl font-bold tabular-nums text-purple-400">{data?.system_error_count || 0}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-2">System Log Errors</p>
        </div>
      </div>

      {/* Zero State */}
      {!loading && totalErrors === 0 && (
        <Card>
          <CardContent className="py-16 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/10 mb-4">
              <ShieldAlert className="h-8 w-8 text-emerald-400" />
            </div>
            <p className="text-lg font-medium">All Clear</p>
            <p className="text-sm text-muted-foreground mt-1">No errors found in pipeline runs or system logs</p>
          </CardContent>
        </Card>
      )}

      {/* Error Tabs */}
      {totalErrors > 0 && (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="all">All ({totalErrors})</TabsTrigger>
            <TabsTrigger value="pipeline">Pipeline ({data?.pipeline_error_count || 0})</TabsTrigger>
            <TabsTrigger value="system">System ({data?.system_error_count || 0})</TabsTrigger>
          </TabsList>

          {/* Pipeline Errors */}
          <TabsContent value="all" className="space-y-2 mt-4">
            {pipelineErrors.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1">Pipeline Failures</p>
                {pipelineErrors.map((err, i) => {
                  const key = `pipeline-${err.run_id}-${i}`;
                  const expanded = expandedItems.has(key);
                  return (
                    <Card key={key} className="border-red-500/10 hover:border-red-500/20 transition-colors">
                      <CardContent className="py-3">
                        <button className="w-full text-left" onClick={() => toggleExpand(key)}>
                          <div className="flex items-center gap-3">
                            <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                            <span className="text-xs font-mono text-muted-foreground">Run #{err.run_id}</span>
                            <Badge variant="outline" className="text-[10px]">{err.phase}</Badge>
                            <span className="flex-1 text-sm truncate">{err.summary || "Pipeline execution failed"}</span>
                            <span className="text-xs text-muted-foreground">{timeAgo(err.timestamp)}</span>
                            {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                          </div>
                        </button>
                        {expanded && err.errors && (
                          <div className="mt-3 pt-3 border-t border-red-500/10">
                            <pre className="text-xs font-mono text-red-300/80 bg-red-500/5 rounded-md p-3 whitespace-pre-wrap overflow-x-auto">
                              {JSON.stringify(err.errors, null, 2)}
                            </pre>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}

            {systemErrors.length > 0 && (
              <div className="space-y-2 mt-4">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1">System Log Errors</p>
                {Object.entries(moduleGroups).map(([module, errors]) => (
                  <div key={module} className="space-y-1.5">
                    <div className="flex items-center gap-2 px-1">
                      <Server className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs font-mono text-muted-foreground">{module}</span>
                      <Badge variant="outline" className="text-[10px] text-red-400 border-red-400/30">{errors.length}</Badge>
                    </div>
                    {errors.map((err, i) => {
                      const key = `sys-${err.log_id}-${i}`;
                      const expanded = expandedItems.has(key);
                      return (
                        <Card key={key} className="border-border hover:border-foreground/15 transition-colors ml-4">
                          <CardContent className="py-3">
                            <button className="w-full text-left" onClick={() => toggleExpand(key)}>
                              <div className="flex items-center gap-3">
                                <SeverityIndicator result={err.result} />
                                <span className="text-xs font-mono text-muted-foreground">#{err.log_id}</span>
                                <span className="flex-1 text-sm truncate">{err.action} → {err.target || "—"}</span>
                                <span className="text-xs text-muted-foreground">{timeAgo(err.timestamp)}</span>
                                {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                              </div>
                            </button>
                            {expanded && (
                              <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div><span className="text-muted-foreground">Action:</span> <span className="font-mono">{err.action}</span></div>
                                  <div><span className="text-muted-foreground">Target:</span> <span className="font-mono">{err.target || "—"}</span></div>
                                  <div><span className="text-muted-foreground">Time:</span> <span className="font-mono">{formatDate(err.timestamp)}</span></div>
                                </div>
                                <div className="rounded-md bg-red-500/5 border border-red-500/10 p-3">
                                  <p className="text-xs font-mono text-red-300/80 whitespace-pre-wrap">{err.result}</p>
                                </div>
                                {err.notes && (
                                  <p className="text-xs text-muted-foreground italic">{err.notes}</p>
                                )}
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="pipeline" className="space-y-2 mt-4">
            {pipelineErrors.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No pipeline failures</CardContent></Card>
            ) : (
              pipelineErrors.map((err, i) => {
                const key = `pt-${err.run_id}-${i}`;
                const expanded = expandedItems.has(key);
                return (
                  <Card key={key} className="border-red-500/10 hover:border-red-500/20 transition-colors">
                    <CardContent className="py-3">
                      <button className="w-full text-left" onClick={() => toggleExpand(key)}>
                        <div className="flex items-center gap-3">
                          <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
                          <span className="text-xs font-mono text-muted-foreground">Run #{err.run_id}</span>
                          <Badge variant="outline" className="text-[10px]">{err.phase}</Badge>
                          <span className="flex-1 text-sm truncate">{err.summary || "Pipeline execution failed"}</span>
                          <span className="text-xs text-muted-foreground">{formatDate(err.timestamp)}</span>
                          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                        </div>
                      </button>
                      {expanded && err.errors && (
                        <div className="mt-3 pt-3 border-t border-red-500/10">
                          <pre className="text-xs font-mono text-red-300/80 bg-red-500/5 rounded-md p-3 whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(err.errors, null, 2)}
                          </pre>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            )}
          </TabsContent>

          <TabsContent value="system" className="space-y-2 mt-4">
            {systemErrors.length === 0 ? (
              <Card><CardContent className="py-8 text-center text-muted-foreground text-sm">No system errors</CardContent></Card>
            ) : (
              systemErrors.map((err, i) => {
                const key = `st-${err.log_id}-${i}`;
                const expanded = expandedItems.has(key);
                return (
                  <Card key={key} className="hover:border-foreground/15 transition-colors">
                    <CardContent className="py-3">
                      <button className="w-full text-left" onClick={() => toggleExpand(key)}>
                        <div className="flex items-center gap-3">
                          <SeverityIndicator result={err.result} />
                          <span className="text-xs font-mono text-muted-foreground">#{err.log_id}</span>
                          <Badge variant="outline" className="text-[10px] font-mono">{err.module}</Badge>
                          <span className="flex-1 text-sm truncate">{err.action} → {err.target || "—"}</span>
                          <span className="text-xs text-muted-foreground">{timeAgo(err.timestamp)}</span>
                          {expanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                        </div>
                      </button>
                      {expanded && (
                        <div className="mt-3 pt-3 border-t border-border/50 space-y-2">
                          <div className="rounded-md bg-red-500/5 border border-red-500/10 p-3">
                            <p className="text-xs font-mono text-red-300/80 whitespace-pre-wrap">{err.result}</p>
                          </div>
                          {err.notes && <p className="text-xs text-muted-foreground italic">{err.notes}</p>}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
