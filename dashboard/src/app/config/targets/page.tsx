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
const CAT_COLORS: Record<string, string> = { ai_leader: "bg-blue-500", ops_supply_chain: "bg-green-500", network: "bg-purple-500", industry_analyst: "bg-orange-500", content_creator: "bg-pink-500" };

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
    if (target) {
      await updateTarget(target.name, payload);
    } else {
      await createTarget(payload);
    }
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div>
        <Label>Name</Label>
        <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Simon Sinek" disabled={!!target} />
      </div>
      <div>
        <Label>LinkedIn URL</Label>
        <Input value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} placeholder="https://linkedin.com/in/..." />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label>Priority (1-10)</Label>
          <Input type="number" min={1} max={10} value={priority} onChange={e => setPriority(Number(e.target.value))} />
        </div>
      </div>
      <div>
        <Label>Notes</Label>
        <Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !name.trim() || !linkedinUrl.trim()}>{saving ? "Saving..." : target ? "Update" : "Create"}</Button>
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Target className="h-6 w-6" />Comment Targets</h2>
        <Button onClick={openCreate} className="flex items-center gap-2"><Plus className="h-4 w-4" />Add Target</Button>
      </div>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingTarget ? "Edit Target" : "New Target"}</DialogTitle></DialogHeader>
          <TargetForm target={editingTarget} onSave={refetch} onClose={() => setDialogOpen(false)} />
        </DialogContent>
      </Dialog>
      {loading && <p className="text-muted-foreground">Loading...</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b"><th className="text-left py-2">Name</th><th>Category</th><th>Priority</th><th>Last Comment</th><th>Actions</th></tr></thead>
          <tbody>
            {data?.map((t) => (
              <tr key={t.name} className="border-b last:border-0">
                <td className="py-2">
                  <a href={t.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline flex items-center gap-1">
                    {t.name}<ExternalLink className="h-3 w-3" />
                  </a>
                </td>
                <td><Badge className={CAT_COLORS[t.category] || "bg-gray-500"}>{t.category}</Badge></td>
                <td className="text-center">{t.priority}</td>
                <td className="text-xs text-muted-foreground">{t.last_comment_date || "Never"}</td>
                <td className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(t)}><Pencil className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="sm" onClick={() => deleteTarget(t.name).then(refetch)}><Trash2 className="h-4 w-4" /></Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
