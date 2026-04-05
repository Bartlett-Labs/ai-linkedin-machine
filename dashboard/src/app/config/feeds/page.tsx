"use client";

import { useState, useEffect, useCallback } from "react";
import { getFeeds, createFeed, updateFeed, deleteFeed, type FeedSource } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Rss, Plus, RefreshCw, ExternalLink, Trash2,
  Edit3, Globe, Clock, CheckCircle2, XCircle,
} from "lucide-react";

const CATEGORY_COLORS: Record<string, string> = {
  ai:           "text-[#06b6d4]   border-[#06b6d4]/30   bg-[#06b6d4]/10",
  automation:   "text-[#a7b0b8]   border-[#a7b0b8]/30   bg-[#a7b0b8]/10",
  ops:          "text-[#22c55e]   border-[#22c55e]/30   bg-[#22c55e]/10",
  tech:         "text-[#2dd4bf]   border-[#2dd4bf]/30   bg-[#2dd4bf]/10",
  business:     "text-[#f59e0b]   border-[#f59e0b]/30   bg-[#f59e0b]/10",
  career:       "text-[#fb923c]   border-[#fb923c]/30   bg-[#fb923c]/10",
  "":           "text-[#73808c]   border-[#73808c]/30   bg-[#73808c]/10",
};

function formatDate(iso: string | null) {
  if (!iso) return "Never";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function FeedForm({
  initial, onSubmit, submitLabel,
}: {
  initial?: Partial<FeedSource>;
  onSubmit: (data: { name: string; url: string; type: string; category: string; active: boolean }) => void;
  submitLabel: string;
}) {
  const [name, setName] = useState(initial?.name || "");
  const [url, setUrl] = useState(initial?.url || "");
  const [type, setType] = useState(initial?.type || "rss");
  const [category, setCategory] = useState(initial?.category || "");
  const [active, setActive] = useState(initial?.active ?? true);

  return (
    <div className="space-y-4 pt-2">
      <div className="space-y-1.5">
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">Feed Name</Label>
        <Input value={name} onChange={e => setName(e.target.value)} placeholder="MIT Technology Review — AI" />
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">URL</Label>
        <Input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com/feed.xml" className="font-mono-data text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Type</Label>
          <Select value={type} onValueChange={setType}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="rss">RSS</SelectItem>
              <SelectItem value="atom">Atom</SelectItem>
              <SelectItem value="json">JSON Feed</SelectItem>
              <SelectItem value="scraper">Web Scraper</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-[#73808c] uppercase tracking-wider">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger><SelectValue placeholder="Select..." /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ai">AI</SelectItem>
              <SelectItem value="automation">Automation</SelectItem>
              <SelectItem value="ops">Operations</SelectItem>
              <SelectItem value="tech">Technology</SelectItem>
              <SelectItem value="business">Business</SelectItem>
              <SelectItem value="career">Career</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div>
          <Label className="text-sm">Active</Label>
          <p className="text-xs text-[#73808c]">Include this feed in ingestion runs</p>
        </div>
        <Switch checked={active} onCheckedChange={setActive} />
      </div>
      <Button onClick={() => onSubmit({ name, url, type, category, active })} className="w-full bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]" disabled={!name.trim() || !url.trim()}>
        {submitLabel}
      </Button>
    </div>
  );
}

export default function FeedsPage() {
  const [feeds, setFeeds] = useState<FeedSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [editFeed, setEditFeed] = useState<FeedSource | null>(null);

  const fetchFeeds = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getFeeds(false);
      setFeeds(res.feeds);
    } catch (e) {
      console.error("Failed to fetch feeds:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchFeeds(); }, [fetchFeeds]);

  const handleCreate = async (data: { name: string; url: string; type: string; category: string; active: boolean }) => {
    await createFeed(data);
    setCreateOpen(false);
    fetchFeeds();
  };

  const handleUpdate = async (data: { name: string; url: string; type: string; category: string; active: boolean }) => {
    if (!editFeed) return;
    await updateFeed(editFeed.id, data);
    setEditFeed(null);
    fetchFeeds();
  };

  const handleDelete = async (id: number) => {
    await deleteFeed(id);
    fetchFeeds();
  };

  const handleToggleActive = async (feed: FeedSource) => {
    await updateFeed(feed.id, { active: !feed.active });
    fetchFeeds();
  };

  const activeCount = feeds.filter(f => f.active).length;
  const inactiveCount = feeds.filter(f => !f.active).length;

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Rss className="h-5 w-5 text-[#06b6d4]" />Feed Sources
          </h2>
          <p className="text-sm text-[#73808c] mt-1">Manage RSS feeds for content ingestion pipeline</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchFeeds} disabled={loading} className="gap-1.5">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />Refresh
          </Button>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Feed</Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader><DialogTitle>Add Feed Source</DialogTitle></DialogHeader>
              <FeedForm onSubmit={handleCreate} submitLabel="Add Feed" />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-[10px] border border-[#2a3138] p-3">
          <div className="flex items-center justify-between">
            <Rss className="h-4 w-4 text-[#73808c]" />
            <span className="text-2xl font-semibold font-mono-data">{feeds.length}</span>
          </div>
          <p className="text-xs text-[#73808c] mt-1">Total Feeds</p>
        </div>
        <div className="rounded-[10px] border border-[#2a3138] p-3">
          <div className="flex items-center justify-between">
            <CheckCircle2 className="h-4 w-4 text-[#22c55e]" />
            <span className="text-2xl font-semibold font-mono-data text-[#22c55e]">{activeCount}</span>
          </div>
          <p className="text-xs text-[#73808c] mt-1">Active</p>
        </div>
        <div className="rounded-[10px] border border-[#2a3138] p-3">
          <div className="flex items-center justify-between">
            <XCircle className="h-4 w-4 text-[#73808c]" />
            <span className="text-2xl font-semibold font-mono-data text-[#73808c]">{inactiveCount}</span>
          </div>
          <p className="text-xs text-[#73808c] mt-1">Inactive</p>
        </div>
      </div>

      {/* Feed Cards */}
      {loading && feeds.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-[#73808c]">Loading feeds...</CardContent></Card>
      ) : feeds.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Rss className="h-8 w-8 text-[#2a3138] mx-auto mb-3" />
            <p className="text-sm text-[#a7b0b8]">No feed sources configured</p>
            <p className="text-xs text-[#73808c] mt-1">Add RSS feeds to power the content ingestion pipeline</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {feeds.map(feed => {
            const catColors = CATEGORY_COLORS[feed.category] || CATEGORY_COLORS[""];
            return (
              <Card key={feed.id} className={`group transition-all ${feed.active ? "hover:border-[#f3f5f7]/15" : "opacity-60"}`}>
                <CardContent className="py-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Globe className={`h-4 w-4 flex-shrink-0 ${feed.active ? "text-[#f3f5f7]" : "text-[#73808c]"}`} />
                        <h3 className="text-sm font-medium truncate">{feed.name}</h3>
                      </div>
                      <a href={feed.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-[#73808c] hover:text-[#06b6d4] mt-1.5 transition-colors font-mono-data truncate max-w-full">
                        <ExternalLink className="h-3 w-3 flex-shrink-0" />
                        <span className="truncate">{feed.url}</span>
                      </a>
                    </div>
                    <Switch checked={feed.active} onCheckedChange={() => handleToggleActive(feed)} />
                  </div>

                  <div className="flex items-center gap-2 mt-3">
                    <Badge variant="outline" className="text-[10px] font-mono-data">{feed.type}</Badge>
                    {feed.category && (
                      <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-full border ${catColors}`}>
                        {feed.category}
                      </span>
                    )}
                    <div className="flex-1" />
                    <div className="flex items-center gap-1 text-[10px] text-[#73808c]/60">
                      <Clock className="h-3 w-3" />
                      <span className="font-mono-data">{formatDate(feed.last_fetched)}</span>
                    </div>
                  </div>

                  <div className="flex gap-1.5 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setEditFeed(feed)}>
                      <Edit3 className="h-3 w-3 mr-1" />Edit
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-[#ef4444] hover:text-[#ef4444]/80 hover:bg-[#ef4444]/10">
                          <Trash2 className="h-3 w-3 mr-1" />Remove
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Remove Feed Source</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete &ldquo;{feed.name}&rdquo;. This action cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction className="bg-[#ef4444] hover:bg-[#ef4444]/80 text-white" onClick={() => handleDelete(feed.id)}>
                            Delete
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editFeed} onOpenChange={open => !open && setEditFeed(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>Edit Feed Source</DialogTitle></DialogHeader>
          {editFeed && (
            <FeedForm initial={editFeed} onSubmit={handleUpdate} submitLabel="Save Changes" />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
