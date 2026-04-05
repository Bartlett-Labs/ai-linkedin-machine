"use client";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";
import { getPersonas, updatePersona } from "@/lib/api";
import type { PersonaSummary } from "@/lib/api";
import { Users, Pencil } from "lucide-react";

function PersonaEditForm({ persona, onSave, onClose }: { persona: PersonaSummary; onSave: () => void; onClose: () => void }) {
  const behavior = (persona.behavior || {}) as Record<string, unknown>;
  const [displayName, setDisplayName] = useState(persona.display_name);
  const [location, setLocation] = useState(persona.location ?? "");
  const [postFrequency, setPostFrequency] = useState(Number(behavior.post_frequency ?? 0));
  const [commentFrequency, setCommentFrequency] = useState(Number(behavior.comment_frequency ?? 0));
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await updatePersona(persona.name, {
      display_name: displayName, location: location || null,
      behavior: { ...behavior, post_frequency: postFrequency, comment_frequency: commentFrequency },
    });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-[#73808c]">Editing: <span className="text-[#f3f5f7]">{persona.name}</span></p>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Display Name</Label><Input value={displayName} onChange={e => setDisplayName(e.target.value)} /></div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Location</Label><Input value={location} onChange={e => setLocation(e.target.value)} placeholder="e.g. Austin, TX" /></div>
      <div className="grid grid-cols-2 gap-4">
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Post Frequency (/ week)</Label><Input type="number" min={0} value={postFrequency} onChange={e => setPostFrequency(Number(e.target.value))} className="font-mono-data" /></div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Comment Frequency (/ day)</Label><Input type="number" min={0} value={commentFrequency} onChange={e => setCommentFrequency(Number(e.target.value))} className="font-mono-data" /></div>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : "Update"}</Button>
      </div>
    </div>
  );
}

export default function PersonasConfigPage() {
  const { data, loading, refetch } = useApi<PersonaSummary[]>(getPersonas);
  const [editingPersona, setEditingPersona] = useState<PersonaSummary | null>(null);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <Users className="h-5 w-5 text-[#06b6d4]" />Personas
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Phantom persona profiles and engagement frequencies</p>
      </div>
      <Dialog open={!!editingPersona} onOpenChange={(open) => { if (!open) setEditingPersona(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Persona</DialogTitle></DialogHeader>
          {editingPersona && <PersonaEditForm persona={editingPersona} onSave={refetch} onClose={() => setEditingPersona(null)} />}
        </DialogContent>
      </Dialog>
      {loading && <p className="text-[#73808c] text-sm">Loading...</p>}
      <div className="grid gap-3">
        {data?.map((p) => (
          <Card key={p.name} className="hover:border-[#f3f5f7]/15 transition-colors">
            <CardContent className="pt-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-medium">{p.display_name}</p>
                  <p className="text-xs text-[#73808c] font-mono-data">{p.name}</p>
                  <p className="text-sm mt-2 text-[#a7b0b8]">{p.persona}</p>
                  {p.location && <p className="text-xs text-[#73808c] mt-1">{p.location}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <div className="text-right text-xs space-y-1">
                    {p.behavior && <Badge variant="outline" className="text-[10px] font-mono-data">Posts: {String((p.behavior as Record<string, unknown>).post_frequency)}/wk</Badge>}
                    {p.behavior && <Badge variant="outline" className="text-[10px] font-mono-data">Comments: {String((p.behavior as Record<string, unknown>).comment_frequency)}/day</Badge>}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setEditingPersona(p)}><Pencil className="h-4 w-4" /></Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
