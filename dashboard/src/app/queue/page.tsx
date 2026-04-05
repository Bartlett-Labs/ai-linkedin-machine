"use client";

import { useState, useEffect, useCallback } from "react";
import { getQueue, getQueueStats, updateQueueItem, createQueueItem, type QueueItem, type QueueStats } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  CheckCircle2, XCircle, Edit3, Plus, RefreshCw,
  Clock, Send, SkipForward, AlertCircle, Inbox,
  ChevronLeft, ChevronRight, User, ExternalLink,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  READY:       { label: "Ready",       color: "text-[#f59e0b]",   bg: "bg-[#f59e0b]/10", border: "border-[#f59e0b]/30" },
  IN_PROGRESS: { label: "In Progress", color: "text-[#06b6d4]",   bg: "bg-[#06b6d4]/10", border: "border-[#06b6d4]/30" },
  DONE:        { label: "Done",        color: "text-[#22c55e]",   bg: "bg-[#22c55e]/10", border: "border-[#22c55e]/30" },
  FAILED:      { label: "Failed",      color: "text-[#ef4444]",   bg: "bg-[#ef4444]/10", border: "border-[#ef4444]/30" },
  SKIPPED:     { label: "Skipped",     color: "text-[#73808c]",   bg: "bg-[#73808c]/10", border: "border-[#73808c]/30" },
};

const STATUS_FILTERS = ["", "READY", "IN_PROGRESS", "DONE", "FAILED", "SKIPPED"];

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: "text-[#73808c]", bg: "bg-[#73808c]/10", border: "border-[#73808c]/30" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full border ${cfg.color} ${cfg.bg} ${cfg.border}`}>
      {status === "READY" && <Clock className="h-3 w-3" />}
      {status === "IN_PROGRESS" && <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#06b6d4] opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-[#06b6d4]" /></span>}
      {status === "DONE" && <CheckCircle2 className="h-3 w-3" />}
      {status === "FAILED" && <XCircle className="h-3 w-3" />}
      {status === "SKIPPED" && <SkipForward className="h-3 w-3" />}
      {cfg.label}
    </span>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export default function QueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [editItem, setEditItem] = useState<QueueItem | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newDraft, setNewDraft] = useState("");
  const [newPersona, setNewPersona] = useState("MainUser");
  const [newType, setNewType] = useState("post");
  const [newTarget, setNewTarget] = useState("");
  const LIMIT = 25;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [queueRes, statsRes] = await Promise.all([
        getQueue({ status: statusFilter, limit: LIMIT, offset: page * LIMIT }),
        getQueueStats(),
      ]);
      setItems(queueRes.items);
      setTotal(queueRes.total);
      setStats(statsRes);
    } catch (e) {
      console.error("Failed to fetch queue:", e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAction = async (id: number, status: string) => {
    await updateQueueItem(id, { status });
    fetchData();
  };

  const handleEditSave = async () => {
    if (!editItem) return;
    await updateQueueItem(editItem.id, { draft_text: editDraft, notes: editNotes });
    setEditItem(null);
    fetchData();
  };

  const handleCreate = async () => {
    if (!newDraft.trim()) return;
    await createQueueItem({
      draft_text: newDraft,
      persona: newPersona,
      action_type: newType,
      target_url: newTarget,
    });
    setNewDraft("");
    setNewTarget("");
    setCreateOpen(false);
    fetchData();
  };

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Inbox className="h-5 w-5 text-[#06b6d4]" />
            Outbound Queue
          </h2>
          <p className="text-sm text-[#73808c] mt-1">Review, approve, and manage queued actions before execution</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} className="gap-1.5">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />Refresh
          </Button>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5">
                <Plus className="h-3.5 w-3.5" />New Item
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>Add to Queue</DialogTitle></DialogHeader>
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-[#73808c] uppercase tracking-wider">Persona</Label>
                    <Select value={newPersona} onValueChange={setNewPersona}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {["MainUser", "Marcus Chen", "Dr. Priya Nair", "Jake Morrison", "Rebecca Torres", "Alex Kim", "David Okafor"].map(p =>
                          <SelectItem key={p} value={p}>{p}</SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs text-[#73808c] uppercase tracking-wider">Type</Label>
                    <Select value={newType} onValueChange={setNewType}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="post">Post</SelectItem>
                        <SelectItem value="comment">Comment</SelectItem>
                        <SelectItem value="reply">Reply</SelectItem>
                        <SelectItem value="repost">Repost</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-[#73808c] uppercase tracking-wider">Target URL</Label>
                  <Input value={newTarget} onChange={e => setNewTarget(e.target.value)} placeholder="https://linkedin.com/in/..." />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-[#73808c] uppercase tracking-wider">Content</Label>
                  <Textarea value={newDraft} onChange={e => setNewDraft(e.target.value)} rows={5} placeholder="Draft text..." className="font-mono-data text-sm" />
                </div>
                <Button onClick={handleCreate} className="w-full bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]" disabled={!newDraft.trim()}>
                  <Send className="h-4 w-4 mr-1.5" />Add to Queue
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-6 gap-3">
          {[
            { key: "", label: "Total", value: stats.total, icon: Inbox, color: "#f3f5f7" },
            { key: "READY", label: "Ready", value: stats.READY || 0, icon: Clock, color: "#f59e0b" },
            { key: "IN_PROGRESS", label: "Active", value: stats.IN_PROGRESS || 0, icon: Send, color: "#06b6d4" },
            { key: "DONE", label: "Done", value: stats.DONE || 0, icon: CheckCircle2, color: "#22c55e" },
            { key: "FAILED", label: "Failed", value: stats.FAILED || 0, icon: XCircle, color: "#ef4444" },
            { key: "SKIPPED", label: "Skipped", value: stats.SKIPPED || 0, icon: SkipForward, color: "#73808c" },
          ].map(s => (
            <button
              key={s.label}
              onClick={() => { setStatusFilter(s.key); setPage(0); }}
              className={`rounded-[10px] border p-3 text-left transition-all hover:border-[#f3f5f7]/20 ${
                statusFilter === s.key ? "border-[#06b6d4]/30 bg-[#1b2024]" : "border-[#2a3138]"
              }`}
            >
              <div className="flex items-center justify-between">
                <s.icon className="h-4 w-4" style={{ color: s.color }} />
                <span className="text-2xl font-semibold font-mono-data" style={{ color: s.color }}>{s.value}</span>
              </div>
              <p className="text-xs text-[#73808c] mt-1">{s.label}</p>
            </button>
          ))}
        </div>
      )}

      {/* Queue Items */}
      <div className="space-y-2">
        {loading && items.length === 0 ? (
          <Card><CardContent className="py-12 text-center text-[#73808c]">Loading queue...</CardContent></Card>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center">
              <Inbox className="h-8 w-8 text-[#2a3138] mx-auto mb-3" />
              <p className="text-sm text-[#a7b0b8]">No items {statusFilter ? `with status "${statusFilter}"` : "in queue"}</p>
            </CardContent>
          </Card>
        ) : (
          items.map(item => (
            <Card key={item.id} className="group hover:border-[#f3f5f7]/15 transition-colors">
              <CardContent className="py-4">
                <div className="flex gap-4">
                  {/* Left: metadata column */}
                  <div className="w-40 flex-shrink-0 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono-data text-[#73808c]">#{item.id}</span>
                      <StatusBadge status={item.status} />
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-[#73808c]">
                      <User className="h-3 w-3" />
                      <span className="truncate">{item.persona}</span>
                    </div>
                    <Badge variant="outline" className="text-[10px] font-mono-data">{item.action_type}</Badge>
                    <p className="text-[10px] text-[#73808c]/60 font-mono-data">{formatDate(item.created_at)}</p>
                  </div>

                  {/* Center: content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm leading-relaxed whitespace-pre-wrap line-clamp-3">{item.draft_text}</p>
                    {item.target_url && (
                      <a href={item.target_url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-[#06b6d4]/70 hover:text-[#06b6d4] mt-2 transition-colors">
                        <ExternalLink className="h-3 w-3" />{item.target_url.substring(0, 60)}...
                      </a>
                    )}
                    {item.notes && (
                      <p className="text-xs text-[#73808c]/60 mt-1 italic">Note: {item.notes}</p>
                    )}
                  </div>

                  {/* Right: actions */}
                  <div className="flex-shrink-0 flex flex-col gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {item.status === "READY" && (
                      <>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-[#22c55e]/30 text-[#22c55e] hover:bg-[#22c55e]/10"
                              onClick={() => handleAction(item.id, "IN_PROGRESS")}>
                              <CheckCircle2 className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Approve</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button size="sm" variant="outline" className="h-8 w-8 p-0 border-[#ef4444]/30 text-[#ef4444] hover:bg-[#ef4444]/10"
                              onClick={() => handleAction(item.id, "SKIPPED")}>
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Reject</TooltipContent>
                        </Tooltip>
                      </>
                    )}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0"
                          onClick={() => { setEditItem(item); setEditDraft(item.draft_text); setEditNotes(item.notes); }}>
                          <Edit3 className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Edit</TooltipContent>
                    </Tooltip>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <p className="text-xs text-[#73808c] font-mono-data">
            Showing {page * LIMIT + 1}&ndash;{Math.min((page + 1) * LIMIT, total)} of {total}
          </p>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editItem} onOpenChange={open => !open && setEditItem(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Queue Item <span className="font-mono-data">#{editItem?.id}</span></DialogTitle></DialogHeader>
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label className="text-xs text-[#73808c] uppercase tracking-wider">Draft Text</Label>
              <Textarea value={editDraft} onChange={e => setEditDraft(e.target.value)} rows={6} className="font-mono-data text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-[#73808c] uppercase tracking-wider">Notes</Label>
              <Input value={editNotes} onChange={e => setEditNotes(e.target.value)} />
            </div>
            <Button onClick={handleEditSave} className="w-full bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">Save Changes</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
