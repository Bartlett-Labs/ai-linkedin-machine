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
      posts_per_week: postsPerWeek, comments_per_day_min: commentsMin, comments_per_day_max: commentsMax,
      phantom_comments_min: phantomMin, phantom_comments_max: phantomMax, min_delay_sec: minDelay, max_likes_per_day: maxLikes,
    });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-[#73808c]">Editing: <span className="text-[#f3f5f7] capitalize">{config.mode}</span></p>
      <div className="grid grid-cols-2 gap-4">
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Posts / Week</Label><Input type="number" min={0} value={postsPerWeek} onChange={e => setPostsPerWeek(Number(e.target.value))} className="font-mono-data" /></div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Max Likes / Day</Label><Input type="number" min={0} value={maxLikes} onChange={e => setMaxLikes(Number(e.target.value))} className="font-mono-data" /></div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Comments / Day (Min)</Label><Input type="number" min={0} value={commentsMin} onChange={e => setCommentsMin(Number(e.target.value))} className="font-mono-data" /></div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Comments / Day (Max)</Label><Input type="number" min={0} value={commentsMax} onChange={e => setCommentsMax(Number(e.target.value))} className="font-mono-data" /></div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Phantom Comments (Min)</Label><Input type="number" min={0} value={phantomMin} onChange={e => setPhantomMin(Number(e.target.value))} className="font-mono-data" /></div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Phantom Comments (Max)</Label><Input type="number" min={0} value={phantomMax} onChange={e => setPhantomMax(Number(e.target.value))} className="font-mono-data" /></div>
      </div>
      <div>
        <Label className="text-xs text-[#73808c] uppercase tracking-wider">Min Delay (seconds)</Label>
        <Input type="number" min={0} value={minDelay} onChange={e => setMinDelay(Number(e.target.value))} className="font-mono-data" />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : "Update"}</Button>
      </div>
    </div>
  );
}

export default function ScheduleConfigPage() {
  const windows = useApi<ActivityWindow[]>(getActivityWindows);
  const configs = useApi<ScheduleConfig[]>(getScheduleConfigs);
  const [editConfig, setEditConfig] = useState<ScheduleConfig | null>(null);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <Calendar className="h-5 w-5 text-[#06b6d4]" />Schedule Configuration
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Activity windows and per-phase rate limits</p>
      </div>
      <Dialog open={!!editConfig} onOpenChange={(open) => { if (!open) setEditConfig(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Rate Limits</DialogTitle></DialogHeader>
          {editConfig && <ScheduleEditForm config={editConfig} onSave={configs.refetch} onClose={() => setEditConfig(null)} />}
        </DialogContent>
      </Dialog>
      <Card>
        <CardHeader><CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Activity Windows</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#2a3138]">
                  <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Window</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Start</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">End</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Days</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Enabled</th>
                </tr>
              </thead>
              <tbody>
                {windows.data?.map((w) => (
                  <tr key={w.window_name} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                    <td className="py-2.5 px-3 text-[#a7b0b8]">{w.window_name}</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{w.start_hour}:00</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{w.end_hour}:00</td>
                    <td className="text-center py-2.5 px-3 font-mono-data text-[#73808c]">{w.days_of_week}</td>
                    <td className="text-center py-2.5 px-3">
                      <Badge className={w.enabled
                        ? "bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/25"
                        : "bg-[#73808c]/15 text-[#73808c] border border-[#73808c]/25"
                      }>{w.enabled ? "Yes" : "No"}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Per-Phase Rate Limits</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#2a3138]">
                  <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Mode</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Posts/Week</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Comments/Day</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Phantom</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Min Delay</th>
                  <th className="text-center py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Max Likes</th>
                  <th className="py-2.5 px-3"></th>
                </tr>
              </thead>
              <tbody>
                {configs.data?.map((c) => (
                  <tr key={c.mode} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                    <td className="py-2.5 px-3 font-medium capitalize text-[#a7b0b8]">{c.mode}</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{c.posts_per_week}</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{c.comments_per_day_min}-{c.comments_per_day_max}</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{c.phantom_comments_min}-{c.phantom_comments_max}</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{c.min_delay_sec}s</td>
                    <td className="text-center py-2.5 px-3 font-mono-data">{c.max_likes_per_day}</td>
                    <td className="py-2.5 px-3"><Button variant="ghost" size="sm" onClick={() => setEditConfig(c)}><Pencil className="h-4 w-4" /></Button></td>
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
