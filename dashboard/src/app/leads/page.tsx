"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useApi } from "@/hooks/use-api";
import { getLeads, updateLead, deleteLead } from "@/lib/api";
import type { Lead, LeadsResponse } from "@/lib/api";
import {
  Target, User, Briefcase, Star, ExternalLink, Trash2,
  MessageSquare, Clock, TrendingUp, Loader2, AlertTriangle,
  Eye, CheckCircle2, XCircle, Archive,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ComponentType<{ className?: string }> }> = {
  new: { label: "New", color: "bg-[#06b6d4]/20 text-[#06b6d4] border-[#06b6d4]/30", icon: Star },
  reviewing: { label: "Reviewing", color: "bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/30", icon: Eye },
  qualified: { label: "Qualified", color: "bg-[#22c55e]/20 text-[#22c55e] border-[#22c55e]/30", icon: CheckCircle2 },
  contacted: { label: "Contacted", color: "bg-[#a7b0b8]/20 text-[#a7b0b8] border-[#a7b0b8]/30", icon: MessageSquare },
  dismissed: { label: "Dismissed", color: "bg-[#1b2024] text-[#73808c] border-[#2a3138]", icon: XCircle },
  archived: { label: "Archived", color: "bg-[#1b2024]/50 text-[#73808c]/70 border-[#2a3138]/50", icon: Archive },
};

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 50 ? "bg-[#22c55e]/15 text-[#22c55e] border-[#22c55e]/25" :
    score >= 30 ? "bg-[#f59e0b]/15 text-[#f59e0b] border-[#f59e0b]/25" :
    "bg-[#1b2024] text-[#73808c] border-[#2a3138]";
  return (
    <Badge variant="outline" className={`font-mono-data text-xs ${color}`}>
      {score}
    </Badge>
  );
}

function LeadDetailDialog({
  lead, open, onClose, onUpdate,
}: {
  lead: Lead; open: boolean; onClose: () => void; onUpdate: () => void;
}) {
  const [status, setStatus] = useState(lead.status);
  const [notes, setNotes] = useState(lead.notes || "");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await updateLead(lead.name, { status, notes: notes || undefined });
    setSaving(false);
    onUpdate();
    onClose();
  };

  const handleDelete = async () => {
    setDeleting(true);
    await deleteLead(lead.name);
    setDeleting(false);
    onUpdate();
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-[#06b6d4]" />
            {lead.name}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-0.5">
              <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Title</span>
              <p className="text-sm">{lead.title || "Unknown"}</p>
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Company</span>
              <p className="text-sm">{lead.company || "Unknown"}</p>
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Score</span>
              <div className="flex items-center gap-2">
                <ScoreBadge score={lead.score} />
                <span className="text-xs text-[#73808c]">
                  {lead.score >= 50 ? "High" : lead.score >= 30 ? "Medium" : "Low"} intent
                </span>
              </div>
            </div>
            <div className="space-y-0.5">
              <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Interactions</span>
              <p className="text-sm font-mono-data">{lead.interaction_count}</p>
            </div>
          </div>

          {lead.reasons.length > 0 && (
            <div className="space-y-1">
              <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Signal Reasons</span>
              <div className="flex flex-wrap gap-1.5">
                {lead.reasons.map((r, i) => (
                  <Badge key={i} variant="outline" className="text-[10px]">{r}</Badge>
                ))}
              </div>
            </div>
          )}

          {lead.comment_preview && (
            <div className="space-y-1">
              <span className="text-[10px] text-[#73808c] uppercase tracking-wider">Comment Preview</span>
              <p className="text-xs bg-[#1b2024] p-2.5 rounded-lg border border-[#2a3138]/30 italic text-[#a7b0b8]">
                &ldquo;{lead.comment_preview}&rdquo;
              </p>
            </div>
          )}

          <div className="space-y-1">
            <Label className="text-[10px] text-[#73808c] uppercase tracking-wider">Status</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-[10px] text-[#73808c] uppercase tracking-wider">Notes</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes about this lead..."
              rows={3}
              className="text-sm"
            />
          </div>

          {lead.source_url && (
            <a href={lead.source_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-[#06b6d4]/70 hover:text-[#06b6d4] transition-colors">
              <ExternalLink className="h-3 w-3" />View source post on LinkedIn
            </a>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-[#2a3138]/50">
            <Button variant="ghost" size="sm" className="text-[#ef4444] hover:text-[#ef4444]/80 text-xs gap-1"
              onClick={handleDelete} disabled={deleting}>
              <Trash2 className="h-3.5 w-3.5" />{deleting ? "Deleting..." : "Delete Lead"}
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
              <Button size="sm" onClick={handleSave} disabled={saving}
                className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function LeadRow({ lead, onClick }: { lead: Lead; onClick: () => void }) {
  const cfg = STATUS_CONFIG[lead.status] || STATUS_CONFIG.new;
  const StatusIcon = cfg.icon;
  const discoveredAgo = lead.discovered_at
    ? formatTimeAgo(new Date(lead.discovered_at))
    : "Unknown";

  return (
    <tr className="border-b border-[#2a3138]/30 hover:bg-[#161a1d] transition-colors cursor-pointer group" onClick={onClick}>
      <td className="py-3 px-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-[#1b2024] border border-[#2a3138]/50 flex items-center justify-center shrink-0">
            <User className="h-4 w-4 text-[#a7b0b8]" />
          </div>
          <div>
            <p className="text-sm font-medium group-hover:text-[#f3f5f7]">{lead.name}</p>
            {lead.title && <p className="text-[11px] text-[#73808c] truncate max-w-[200px]">{lead.title}</p>}
          </div>
        </div>
      </td>
      <td className="py-3 px-3">
        <div className="flex items-center gap-1.5 text-xs text-[#73808c]">
          <Briefcase className="h-3 w-3" />{lead.company || "-"}
        </div>
      </td>
      <td className="py-3 px-3"><ScoreBadge score={lead.score} /></td>
      <td className="py-3 px-3">
        <Badge variant="outline" className={`text-[10px] gap-1 ${cfg.color}`}>
          <StatusIcon className="h-3 w-3" />{cfg.label}
        </Badge>
      </td>
      <td className="py-3 px-3">
        <span className="text-xs font-mono-data text-[#73808c]">{lead.interaction_count}</span>
      </td>
      <td className="py-3 px-3">
        <span className="text-xs text-[#73808c] font-mono-data">{discoveredAgo}</span>
      </td>
    </tr>
  );
}

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 1) return "< 1h ago";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return `${Math.floor(days / 7)}w ago`;
}

export default function LeadsPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const leads = useApi<LeadsResponse>(() => getLeads(statusFilter), [statusFilter]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const statusCounts = leads.data?.leads.reduce((acc, l) => {
    acc[l.status] = (acc[l.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Target className="h-5 w-5 text-[#06b6d4]" />
            Leads
          </h2>
          <p className="text-sm text-[#73808c] mt-1">
            Identified through engagement signals &middot; <span className="font-mono-data">{leads.data?.total || 0}</span> total
          </p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card
          className={`cursor-pointer transition-all ${!statusFilter ? "border-[#06b6d4]/30 bg-[#06b6d4]/5" : "hover:bg-[#161a1d]"}`}
          onClick={() => setStatusFilter(undefined)}
        >
          <CardContent className="py-3 px-4">
            <p className="text-xs text-[#73808c]">All</p>
            <p className="text-xl font-semibold font-mono-data mt-0.5">{leads.data?.total || 0}</p>
          </CardContent>
        </Card>
        {(["new", "reviewing", "qualified", "contacted"] as const).map((s) => {
          const cfg = STATUS_CONFIG[s];
          return (
            <Card
              key={s}
              className={`cursor-pointer transition-all ${statusFilter === s ? "border-[#06b6d4]/30 bg-[#06b6d4]/5" : "hover:bg-[#161a1d]"}`}
              onClick={() => setStatusFilter(statusFilter === s ? undefined : s)}
            >
              <CardContent className="py-3 px-4">
                <p className="text-xs text-[#73808c]">{cfg.label}</p>
                <p className="text-xl font-semibold font-mono-data mt-0.5">{statusCounts[s] || 0}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Leads Table */}
      <Card>
        <CardContent className="p-0">
          {leads.loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[#73808c]" />
            </div>
          )}

          {leads.error && (
            <div className="flex items-center gap-2 p-4">
              <AlertTriangle className="h-5 w-5 text-[#f59e0b]" />
              <p className="text-sm text-[#f59e0b]">{leads.error}</p>
            </div>
          )}

          {leads.data && leads.data.leads.length === 0 && (
            <div className="text-center py-12">
              <Target className="h-8 w-8 mx-auto text-[#2a3138] mb-3" />
              <p className="text-sm text-[#a7b0b8]">
                {statusFilter ? `No ${STATUS_CONFIG[statusFilter]?.label || statusFilter} leads` : "No leads identified yet"}
              </p>
              <p className="text-xs text-[#73808c] mt-1">
                Leads are automatically identified from engagement signals
              </p>
            </div>
          )}

          {leads.data && leads.data.leads.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#2a3138]">
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Name</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Company</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Score</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Status</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Interactions</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold text-[#73808c] uppercase tracking-wider">Discovered</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.data.leads.map((lead) => (
                    <LeadRow key={lead.name} lead={lead} onClick={() => setSelectedLead(lead)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedLead && (
        <LeadDetailDialog
          lead={selectedLead}
          open={!!selectedLead}
          onClose={() => setSelectedLead(null)}
          onUpdate={() => { leads.refetch(); setSelectedLead(null); }}
        />
      )}
    </div>
  );
}
