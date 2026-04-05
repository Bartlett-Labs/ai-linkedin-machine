"use client";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/hooks/use-api";
import { getTemplates, createTemplate, deleteTemplate } from "@/lib/api";
import type { CommentTemplate } from "@/lib/api";
import { MessageSquare, Trash2, Plus } from "lucide-react";

const TONES = ["professional", "casual", "technical", "supportive", "contrarian", "academic", "enthusiastic"];
const TEMPLATE_CATEGORIES = ["general", "agreement", "question", "debate", "insight", "anecdote", "challenge"];
const PERSONAS = ["MainUser", "Marcus Chen", "Dr. Priya Nair", "Jake Morrison", "Rebecca Torres", "Alex Kim", "David Okafor"];

function TemplateForm({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [templateText, setTemplateText] = useState("");
  const [tone, setTone] = useState("professional");
  const [category, setCategory] = useState("general");
  const [persona, setPersona] = useState("MainUser");
  const [exampleUse, setExampleUse] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await createTemplate({ template_text: templateText, tone, category, persona, example_use: exampleUse, safety_flag: 0 });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div>
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">Template Text</Label>
        <Textarea value={templateText} onChange={e => setTemplateText(e.target.value)} rows={4} placeholder="Write the comment template..." />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Persona</Label>
          <Select value={persona} onValueChange={setPersona}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{PERSONAS.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Tone</Label>
          <Select value={tone} onValueChange={setTone}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{TONES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{TEMPLATE_CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">Example Use</Label>
        <Input value={exampleUse} onChange={e => setExampleUse(e.target.value)} placeholder="When to use this template..." />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !templateText.trim()} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : "Create"}</Button>
      </div>
    </div>
  );
}

export default function TemplatesConfigPage() {
  const [filterPersona, setFilterPersona] = useState("all");
  const { data, loading, refetch } = useApi<CommentTemplate[]>(() => getTemplates(filterPersona === "all" ? undefined : filterPersona));
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <MessageSquare className="h-5 w-5 text-[#06b6d4]" />Comment Templates
          </h2>
          <p className="text-sm text-[#73808c] mt-1">Fallback comment templates by persona, tone, and category</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Template</Button>
      </div>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>New Template</DialogTitle></DialogHeader>
          <TemplateForm onSave={refetch} onClose={() => setDialogOpen(false)} />
        </DialogContent>
      </Dialog>
      <div className="flex items-center gap-2">
        <Label className="text-sm text-[#73808c]">Filter by persona:</Label>
        <Select value={filterPersona} onValueChange={(v) => { setFilterPersona(v); }}>
          <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Personas</SelectItem>
            {PERSONAS.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={refetch}>Apply</Button>
      </div>
      {loading && <p className="text-[#73808c] text-sm">Loading...</p>}
      <div className="grid gap-3">
        {data?.map((t) => (
          <Card key={t.template_id}>
            <CardContent className="pt-4">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex gap-2 mb-2">
                    <Badge variant="outline" className="text-[10px]">{t.persona}</Badge>
                    {t.tone && <Badge variant="outline" className="text-[10px]">{t.tone}</Badge>}
                    {t.category && <Badge variant="outline" className="text-[10px]">{t.category}</Badge>}
                  </div>
                  <p className="text-sm text-[#a7b0b8]">{t.template_text}</p>
                  {t.example_use && <p className="text-xs text-[#73808c] mt-1">Example: {t.example_use}</p>}
                </div>
                <Button variant="ghost" size="sm" className="text-[#73808c] hover:text-[#ef4444]" onClick={() => deleteTemplate(t.template_id).then(refetch)}><Trash2 className="h-4 w-4" /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
