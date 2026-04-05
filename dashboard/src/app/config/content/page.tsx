"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { getContentBank, getRepostBank, createContentItem, updateContentItem, deleteContentItem, createRepostItem } from "@/lib/api";
import type { ContentBankItem, RepostBankItem } from "@/lib/api";
import { FileText, Trash2, Plus, Pencil, ExternalLink } from "lucide-react";

const CATEGORIES = ["ai_automation", "ops_efficiency", "personal_growth", "builder_stories", "phantom_engagement"];
const POST_TYPES = ["original", "repost", "carousel", "poll", "article"];

function ContentForm({ item, onSave, onClose }: { item?: ContentBankItem; onSave: () => void; onClose: () => void }) {
  const [category, setCategory] = useState(item?.category ?? "ai_automation");
  const [postType, setPostType] = useState(item?.post_type ?? "original");
  const [draft, setDraft] = useState(item?.draft ?? "");
  const [ready, setReady] = useState(item?.ready ?? false);
  const [notes, setNotes] = useState(item?.notes ?? "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    const payload = { category, post_type: postType, draft, ready, notes: notes || null, safety_flag: 0 };
    if (item) { await updateContentItem(item.item_id, payload); } else { await createContentItem(payload); }
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Post Type</Label>
          <Select value={postType} onValueChange={setPostType}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{POST_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">Draft Content</Label>
        <Textarea value={draft} onChange={e => setDraft(e.target.value)} rows={6} placeholder="Write your post content..." />
      </div>
      <div>
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">Notes</Label>
        <Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." />
      </div>
      <div className="flex items-center gap-2">
        <Switch checked={ready} onCheckedChange={setReady} />
        <Label className="text-sm text-[#a7b0b8]">Ready to publish</Label>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !draft.trim()} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : item ? "Update" : "Create"}</Button>
      </div>
    </div>
  );
}

function RepostForm({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [sourceName, setSourceName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [summary, setSummary] = useState("");
  const [commentaryPrompt, setCommentaryPrompt] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await createRepostItem({ source_name: sourceName, source_url: sourceUrl, summary, commentary_prompt: commentaryPrompt, notes: notes || null, safety_flag: 0 });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Source Name</Label><Input value={sourceName} onChange={e => setSourceName(e.target.value)} placeholder="e.g. TechCrunch" /></div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Source URL</Label><Input value={sourceUrl} onChange={e => setSourceUrl(e.target.value)} placeholder="https://..." /></div>
      </div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Summary</Label><Textarea value={summary} onChange={e => setSummary(e.target.value)} rows={3} placeholder="Brief summary of the article..." /></div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Commentary Prompt</Label><Textarea value={commentaryPrompt} onChange={e => setCommentaryPrompt(e.target.value)} rows={2} placeholder="What angle should the commentary take?" /></div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Notes</Label><Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." /></div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !sourceName.trim() || !sourceUrl.trim()} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : "Create"}</Button>
      </div>
    </div>
  );
}

export default function ContentConfigPage() {
  const content = useApi<ContentBankItem[]>(getContentBank);
  const reposts = useApi<RepostBankItem[]>(getRepostBank);
  const [contentDialogOpen, setContentDialogOpen] = useState(false);
  const [repostDialogOpen, setRepostDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<ContentBankItem | undefined>(undefined);

  const openEdit = (item: ContentBankItem) => { setEditingItem(item); setContentDialogOpen(true); };
  const openCreate = () => { setEditingItem(undefined); setContentDialogOpen(true); };

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <FileText className="h-5 w-5 text-[#06b6d4]" />Content Management
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Content bank and repost sources for post generation</p>
      </div>
      <Tabs defaultValue="bank">
        <TabsList><TabsTrigger value="bank">Content Bank</TabsTrigger><TabsTrigger value="reposts">Repost Bank</TabsTrigger></TabsList>
        <TabsContent value="bank" className="mt-4 space-y-4">
          <Dialog open={contentDialogOpen} onOpenChange={setContentDialogOpen}>
            <Button onClick={openCreate} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Content</Button>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>{editingItem ? "Edit Content" : "New Content"}</DialogTitle></DialogHeader>
              <ContentForm item={editingItem} onSave={content.refetch} onClose={() => setContentDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          {content.data?.map((item) => (
            <Card key={item.item_id}>
              <CardContent className="pt-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex gap-2 mb-2">
                      <Badge variant="outline" className="font-mono-data text-[10px]">{item.category}</Badge>
                      <Badge variant="outline" className="text-[10px]">{item.post_type}</Badge>
                      <Badge className={item.ready
                        ? "bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/25"
                        : "bg-[#73808c]/15 text-[#73808c] border border-[#73808c]/25"
                      }>{item.ready ? "Ready" : "Draft"}</Badge>
                    </div>
                    <p className="text-sm line-clamp-3 text-[#a7b0b8]">{item.draft}</p>
                    {item.notes && <p className="text-xs text-[#73808c] mt-1">{item.notes}</p>}
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(item)}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="sm" className="text-[#73808c] hover:text-[#ef4444]" onClick={() => deleteContentItem(item.item_id).then(content.refetch)}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {content.loading && <p className="text-[#73808c] text-sm">Loading...</p>}
        </TabsContent>
        <TabsContent value="reposts" className="mt-4 space-y-4">
          <Dialog open={repostDialogOpen} onOpenChange={setRepostDialogOpen}>
            <Button onClick={() => setRepostDialogOpen(true)} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Repost</Button>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>New Repost</DialogTitle></DialogHeader>
              <RepostForm onSave={reposts.refetch} onClose={() => setRepostDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          {reposts.data?.map((item) => (
            <Card key={item.item_id}>
              <CardContent className="pt-4">
                <p className="font-medium">{item.source_name}</p>
                <a href={item.source_url} className="inline-flex items-center gap-1 text-xs text-[#06b6d4]/70 hover:text-[#06b6d4] transition-colors mt-1" target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-3 w-3" />{item.source_url}
                </a>
                <p className="text-sm mt-2 text-[#a7b0b8]">{item.summary}</p>
                {item.commentary_prompt && <p className="text-xs text-[#73808c] mt-1">Commentary: {item.commentary_prompt}</p>}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}
