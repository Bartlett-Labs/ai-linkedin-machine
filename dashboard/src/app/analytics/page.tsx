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
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2"><BarChart3 className="h-6 w-6" />Analytics</h2>
      {/* Trend Chart */}
      <Card>
        <CardHeader><CardTitle>Engagement Trends (30 Days)</CardTitle></CardHeader>
        <CardContent>
          {trends.data && (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trends.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #333" }} />
                <Legend />
                <Bar dataKey="comments" fill="#3b82f6" name="Comments" />
                <Bar dataKey="posts" fill="#10b981" name="Posts" />
                <Bar dataKey="replies" fill="#f59e0b" name="Replies" />
                <Bar dataKey="likes" fill="#8b5cf6" name="Likes" />
              </BarChart>
            </ResponsiveContainer>
          )}
          {trends.loading && <p className="text-muted-foreground">Loading chart...</p>}
        </CardContent>
      </Card>
      {/* Per-Persona Breakdown */}
      <Card>
        <CardHeader><CardTitle>Per-Persona Breakdown (30 Days)</CardTitle></CardHeader>
        <CardContent>
          {personas.data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b"><th className="text-left py-2">Persona</th><th className="text-right py-2">Total</th><th className="text-right py-2">Comments</th><th className="text-right py-2">Posts</th><th className="text-right py-2">Replies</th></tr></thead>
                <tbody>
                  {personas.data.map((p) => (
                    <tr key={p.persona} className="border-b last:border-0">
                      <td className="py-2">{p.persona}</td>
                      <td className="text-right font-medium">{p.total_actions}</td>
                      <td className="text-right">{p.comments}</td>
                      <td className="text-right">{p.posts}</td>
                      <td className="text-right">{p.replies}</td>
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
