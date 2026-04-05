"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/use-api";
import { getTrends, getPersonaAnalytics, getTodaySummary } from "@/lib/api";
import type { EngagementTrend, PersonaStats, DailySummary } from "@/lib/api";
import { BarChart3 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export default function AnalyticsPage() {
  const today = useApi<DailySummary>(getTodaySummary);
  const trends = useApi<EngagementTrend[]>(() => getTrends(30));
  const personas = useApi<PersonaStats[]>(() => getPersonaAnalytics(30));

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <BarChart3 className="h-5 w-5 text-[#06b6d4]" />Analytics
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Engagement trends and per-persona performance breakdown</p>
      </div>

      {/* Quick stats */}
      {today.data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {([
            ["Comments", today.data.comments_posted, "#06b6d4"],
            ["Posts", today.data.posts_made, "#22c55e"],
            ["Replies", today.data.replies_sent, "#f59e0b"],
            ["Likes", today.data.likes_given, "#a7b0b8"],
          ] as const).map(([label, value, color]) => (
            <Card key={label}>
              <CardContent className="pt-4 pb-4">
                <p className="text-[11px] uppercase tracking-wider font-semibold text-[#73808c]">{label} Today</p>
                <p className="text-2xl font-semibold font-mono-data mt-1" style={{ color: String(color) }}>{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Engagement Trends — 30 Days</CardTitle>
        </CardHeader>
        <CardContent>
          {trends.data && (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trends.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3138" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#73808c" }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11, fill: "#73808c" }} />
                <Tooltip contentStyle={{ backgroundColor: "#161a1d", border: "1px solid #2a3138", borderRadius: "8px", color: "#f3f5f7", fontSize: "12px" }} />
                <Legend wrapperStyle={{ fontSize: "12px", color: "#a7b0b8" }} />
                <Bar dataKey="comments" fill="#06b6d4" name="Comments" radius={[2, 2, 0, 0]} />
                <Bar dataKey="posts" fill="#22c55e" name="Posts" radius={[2, 2, 0, 0]} />
                <Bar dataKey="replies" fill="#f59e0b" name="Replies" radius={[2, 2, 0, 0]} />
                <Bar dataKey="likes" fill="#a7b0b8" name="Likes" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
          {trends.loading && <p className="text-[#73808c] text-sm">Loading chart...</p>}
        </CardContent>
      </Card>

      {/* Per-Persona Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-wider font-semibold text-[#73808c]">Per-Persona Breakdown — 30 Days</CardTitle>
        </CardHeader>
        <CardContent>
          {personas.data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#2a3138]">
                    <th className="text-left py-2.5 px-3 text-[11px] uppercase tracking-wider font-semibold text-[#73808c]">Persona</th>
                    <th className="text-right py-2.5 px-3 text-[11px] uppercase tracking-wider font-semibold text-[#73808c]">Total</th>
                    <th className="text-right py-2.5 px-3 text-[11px] uppercase tracking-wider font-semibold text-[#73808c]">Comments</th>
                    <th className="text-right py-2.5 px-3 text-[11px] uppercase tracking-wider font-semibold text-[#73808c]">Posts</th>
                    <th className="text-right py-2.5 px-3 text-[11px] uppercase tracking-wider font-semibold text-[#73808c]">Replies</th>
                  </tr>
                </thead>
                <tbody>
                  {personas.data.map((p) => (
                    <tr key={p.persona} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                      <td className="py-2.5 px-3 text-[#a7b0b8]">{p.persona}</td>
                      <td className="text-right py-2.5 px-3 font-mono-data font-medium">{p.total_actions}</td>
                      <td className="text-right py-2.5 px-3 font-mono-data text-[#06b6d4]">{p.comments}</td>
                      <td className="text-right py-2.5 px-3 font-mono-data text-[#22c55e]">{p.posts}</td>
                      <td className="text-right py-2.5 px-3 font-mono-data text-[#f59e0b]">{p.replies}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
