"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/use-api";
import { getActivityWindows, getScheduleConfigs, updateScheduleConfig } from "@/lib/api";
import type { ActivityWindow, ScheduleConfig } from "@/lib/api";
import { Calendar, Pencil } from "lucide-react";

function ScheduleEditForm({ config, onSave, onClose }: { config: ScheduleConfig; onSave: () => void; onClose: () => void }) {
  const [postsPerWeek, setPostsPerWeek] = useState(config.posts_per_week);
  const [commentsMin, setCommentsMin] = useState(config.comments_per_day_min);
  const [commentsMax, setCommentsMax] = useState(config.comments_per_day_max);
  const [phantomMin, setPhantomMin] = useState(config.phantom_comments_min);
  const [phantomMax, setPhantomMax] = useState(config.phantom_comments_max);
  const [minDelay, setMinDelay] = useState(config.min_delay_sec);
  const [maxLikes, setMaxLikes] = useState(config.max_likes_per_day);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await updateScheduleConfig(config.mode, {
      posts_per_week: postsPerWeek,
      comments_per_day_min: commentsMin,
      comments_per_day_max: commentsMax,
      phantom_comments_min: phantomMin,
      phantom_comments_max: phantomMax,
      min_delay_sec: minDelay,
      max_likes_per_day: maxLikes,
    });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-muted-foreground">Editing: <span className="text-foreground capitalize">{config.mode}</span></p>
      <div className="grid grid-cols-2 gap-4">
        <div><Label>Posts / Week</Label><Input type="number" min={0} value={postsPerWeek} onChange={e => setPostsPerWeek(Number(e.target.value))} /></div>
        <div><Label>Max Likes / Day</Label><Input type="number" min={0} value={maxLikes} onChange={e => setMaxLikes(Number(e.target.value))} /></div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div><Label>Comments / Day (Min)</Label><Input type="number" min={0} value={commentsMin} onChange={e => setCommentsMin(Number(e.target.value))} /></div>
        <div><Label>Comments / Day (Max)</Label><Input type="number" min={0} value={commentsMax} onChange={e => setCommentsMax(Number(e.target.value))} /></div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div><Label>Phantom Comments (Min)</Label><Input type="number" min={0} value={phantomMin} onChange={e => setPhantomMin(Number(e.target.value))} /></div>
        <div><Label>Phantom Comments (Max)</Label><Input type="number" min={0} value={phantomMax} onChange={e => setPhantomMax(Number(e.target.value))} /></div>
      </div>
      <div>
        <Label>Min Delay (seconds)</Label>
        <Input type="number" min={0} value={minDelay} onChange={e => setMinDelay(Number(e.target.value))} />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving}>{saving ? "Saving..." : "Update"}</Button>
      </div>
    </div>
  );
}

export default function ScheduleConfigPage() {
  const windows = useApi<ActivityWindow[]>(getActivityWindows);
  const configs = useApi<ScheduleConfig[]>(getScheduleConfigs);
  const [editConfig, setEditConfig] = useState<ScheduleConfig | null>(null);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2"><Calendar className="h-6 w-6" />Schedule Configuration</h2>
      <Dialog open={!!editConfig} onOpenChange={(open) => { if (!open) setEditConfig(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Rate Limits</DialogTitle></DialogHeader>
          {editConfig && <ScheduleEditForm config={editConfig} onSave={configs.refetch} onClose={() => setEditConfig(null)} />}
        </DialogContent>
      </Dialog>
      <Card>
        <CardHeader><CardTitle>Activity Windows</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b"><th className="text-left py-2">Window</th><th>Start</th><th>End</th><th>Days</th><th>Enabled</th></tr></thead>
              <tbody>
                {windows.data?.map((w) => (
                  <tr key={w.window_name} className="border-b last:border-0">
                    <td className="py-2">{w.window_name}</td>
                    <td className="text-center">{w.start_hour}:00</td>
                    <td className="text-center">{w.end_hour}:00</td>
                    <td className="text-center">{w.days_of_week}</td>
                    <td className="text-center"><Badge className={w.enabled ? "bg-green-500" : "bg-gray-500"}>{w.enabled ? "Yes" : "No"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Per-Phase Rate Limits</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b"><th className="text-left py-2">Mode</th><th>Posts/Week</th><th>Comments/Day</th><th>Phantom</th><th>Min Delay</th><th>Max Likes</th><th></th></tr></thead>
              <tbody>
                {configs.data?.map((c) => (
                  <tr key={c.mode} className="border-b last:border-0">
                    <td className="py-2 font-medium capitalize">{c.mode}</td>
                    <td className="text-center">{c.posts_per_week}</td>
                    <td className="text-center">{c.comments_per_day_min}-{c.comments_per_day_max}</td>
                    <td className="text-center">{c.phantom_comments_min}-{c.phantom_comments_max}</td>
                    <td className="text-center">{c.min_delay_sec}s</td>
                    <td className="text-center">{c.max_likes_per_day}</td>
                    <td><Button variant="ghost" size="sm" onClick={() => setEditConfig(c)}><Pencil className="h-4 w-4" /></Button></td>
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
