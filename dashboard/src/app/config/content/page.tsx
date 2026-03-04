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
import { FileText, Trash2, Plus, Pencil } from "lucide-react";

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
    if (item) {
      await updateContentItem(item.item_id, payload);
    } else {
      await createContentItem(payload);
    }
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label>Post Type</Label>
          <Select value={postType} onValueChange={setPostType}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{POST_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label>Draft Content</Label>
        <Textarea value={draft} onChange={e => setDraft(e.target.value)} rows={6} placeholder="Write your post content..." />
      </div>
      <div>
        <Label>Notes</Label>
        <Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." />
      </div>
      <div className="flex items-center gap-2">
        <Switch checked={ready} onCheckedChange={setReady} />
        <Label>Ready to publish</Label>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !draft.trim()}>{saving ? "Saving..." : item ? "Update" : "Create"}</Button>
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
        <div><Label>Source Name</Label><Input value={sourceName} onChange={e => setSourceName(e.target.value)} placeholder="e.g. TechCrunch" /></div>
        <div><Label>Source URL</Label><Input value={sourceUrl} onChange={e => setSourceUrl(e.target.value)} placeholder="https://..." /></div>
      </div>
      <div><Label>Summary</Label><Textarea value={summary} onChange={e => setSummary(e.target.value)} rows={3} placeholder="Brief summary of the article..." /></div>
      <div><Label>Commentary Prompt</Label><Textarea value={commentaryPrompt} onChange={e => setCommentaryPrompt(e.target.value)} rows={2} placeholder="What angle should the commentary take?" /></div>
      <div><Label>Notes</Label><Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." /></div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !sourceName.trim() || !sourceUrl.trim()}>{saving ? "Saving..." : "Create"}</Button>
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
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2"><FileText className="h-6 w-6" />Content Management</h2>
      <Tabs defaultValue="bank">
        <TabsList><TabsTrigger value="bank">Content Bank</TabsTrigger><TabsTrigger value="reposts">Repost Bank</TabsTrigger></TabsList>
        <TabsContent value="bank" className="mt-4 space-y-4">
          <Dialog open={contentDialogOpen} onOpenChange={setContentDialogOpen}>
            <Button onClick={openCreate} className="flex items-center gap-2"><Plus className="h-4 w-4" />Add Content</Button>
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
                      <Badge variant="outline">{item.category}</Badge>
                      <Badge variant="outline">{item.post_type}</Badge>
                      <Badge className={item.ready ? "bg-green-500" : "bg-gray-500"}>{item.ready ? "Ready" : "Draft"}</Badge>
                    </div>
                    <p className="text-sm line-clamp-3">{item.draft}</p>
                    {item.notes && <p className="text-xs text-muted-foreground mt-1">{item.notes}</p>}
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(item)}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="sm" onClick={() => deleteContentItem(item.item_id).then(content.refetch)}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {content.loading && <p className="text-muted-foreground">Loading...</p>}
        </TabsContent>
        <TabsContent value="reposts" className="mt-4 space-y-4">
          <Dialog open={repostDialogOpen} onOpenChange={setRepostDialogOpen}>
            <Button onClick={() => setRepostDialogOpen(true)} className="flex items-center gap-2"><Plus className="h-4 w-4" />Add Repost</Button>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>New Repost</DialogTitle></DialogHeader>
              <RepostForm onSave={reposts.refetch} onClose={() => setRepostDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          {reposts.data?.map((item) => (
            <Card key={item.item_id}>
              <CardContent className="pt-4">
                <p className="font-medium">{item.source_name}</p>
                <a href={item.source_url} className="text-xs text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">{item.source_url}</a>
                <p className="text-sm mt-2">{item.summary}</p>
                {item.commentary_prompt && <p className="text-xs text-muted-foreground mt-1">Commentary: {item.commentary_prompt}</p>}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}
