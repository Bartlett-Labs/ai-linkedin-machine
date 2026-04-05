"use client";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { getTargets, createTarget, updateTarget, deleteTarget } from "@/lib/api";
import type { CommentTarget } from "@/lib/api";
import { Target, Trash2, ExternalLink, Plus, Pencil } from "lucide-react";

const CATEGORIES = ["ai_leader", "ops_supply_chain", "network", "industry_analyst", "content_creator"];
const CAT_COLORS: Record<string, string> = {
  ai_leader: "bg-[#06b6d4]/15 text-[#06b6d4] border-[#06b6d4]/25",
  ops_supply_chain: "bg-[#22c55e]/15 text-[#22c55e] border-[#22c55e]/25",
  network: "bg-[#a7b0b8]/15 text-[#a7b0b8] border-[#a7b0b8]/25",
  industry_analyst: "bg-[#fb923c]/15 text-[#fb923c] border-[#fb923c]/25",
  content_creator: "bg-[#f59e0b]/15 text-[#f59e0b] border-[#f59e0b]/25",
};

function TargetForm({ target, onSave, onClose }: { target?: CommentTarget; onSave: () => void; onClose: () => void }) {
  const [name, setName] = useState(target?.name ?? "");
  const [linkedinUrl, setLinkedinUrl] = useState(target?.linkedin_url ?? "");
  const [category, setCategory] = useState(target?.category ?? "ai_leader");
  const [priority, setPriority] = useState(target?.priority ?? 5);
  const [notes, setNotes] = useState(target?.notes ?? "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    const payload = { name, linkedin_url: linkedinUrl, category, priority, notes: notes || null };
    if (target) { await updateTarget(target.name, payload); } else { await createTarget(payload); }
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Name</Label><Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Simon Sinek" disabled={!!target} /></div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">LinkedIn URL</Label><Input value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} placeholder="https://linkedin.com/in/..." className="font-mono-data text-sm" /></div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Priority (1-10)</Label><Input type="number" min={1} max={10} value={priority} onChange={e => setPriority(Number(e.target.value))} className="font-mono-data" /></div>
      </div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Notes</Label><Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." /></div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !name.trim() || !linkedinUrl.trim()} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : target ? "Update" : "Create"}</Button>
      </div>
    </div>
  );
}

export default function TargetsConfigPage() {
  const { data, loading, refetch } = useApi<CommentTarget[]>(getTargets);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState<CommentTarget | undefined>(undefined);

  const openEdit = (t: CommentTarget) => { setEditingTarget(t); setDialogOpen(true); };
  const openCreate = () => { setEditingTarget(undefined); setDialogOpen(true); };

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Target className="h-5 w-5 text-[#06b6d4]" />Comment Targets
          </h2>
          <p className="text-sm text-[#73808c] mt-1">LinkedIn profiles targeted for commenting engagement</p>
        </div>
        <Button onClick={openCreate} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Target</Button>
      </div>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingTarget ? "Edit Target" : "New Target"}</DialogTitle></DialogHeader>
          <TargetForm target={editingTarget} onSave={refetch} onClose={() => setDialogOpen(false)} />
        </DialogContent>
      </Dialog>
      {loading && <p className="text-[#73808c] text-sm">Loading...</p>}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#2a3138]">
                  <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Name</th>
                  <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Category</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Priority</th>
                  <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Last Comment</th>
                  <th className="py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((t) => (
                  <tr key={t.name} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                    <td className="py-2.5 px-3">
                      <a href={t.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-[#06b6d4]/80 hover:text-[#06b6d4] transition-colors flex items-center gap-1">
                        {t.name}<ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                    <td className="py-2.5 px-3"><Badge className={`text-[10px] border ${CAT_COLORS[t.category] || "bg-[#73808c]/15 text-[#73808c] border-[#73808c]/25"}`}>{t.category}</Badge></td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{t.priority}</td>
                    <td className="py-2.5 px-3 text-xs text-[#73808c] font-mono-data">{t.last_comment_date || "Never"}</td>
                    <td className="py-2.5 px-3 flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(t)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="sm" className="text-[#73808c] hover:text-[#ef4444]" onClick={() => deleteTarget(t.name).then(refetch)}><Trash2 className="h-4 w-4" /></Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
