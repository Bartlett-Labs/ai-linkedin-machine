"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";
import { getHistory, exportHistoryCsv } from "@/lib/api";
import type { HistoryResponse } from "@/lib/api";
import { Clock, Download, RefreshCw } from "lucide-react";

export default function HistoryPage() {
  const [offset, setOffset] = useState(0);
  const [actionFilter, setActionFilter] = useState("");
  const limit = 50;
  const { data, loading, refetch } = useApi<HistoryResponse>(
    () => getHistory({ limit, offset, action: actionFilter || undefined }), [offset, actionFilter]
  );

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold flex items-center gap-2.5">
            <Clock className="h-5 w-5 text-[#06b6d4]" />
            Activity History
          </h2>
          <p className="text-sm text-[#73808c] mt-1">Complete system activity log with filtering and export</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refetch} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" />Refresh
          </Button>
          <a href={exportHistoryCsv()} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Download className="h-3.5 w-3.5" />Export CSV
            </Button>
          </a>
        </div>
      </div>
      <div className="flex gap-2">
        <Input placeholder="Filter by action..." value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }} className="max-w-xs" />
        <Button variant="outline" size="sm" onClick={refetch}>Search</Button>
      </div>
      <Card>
        <CardContent className="pt-6">
          {loading && <p className="text-[#73808c] text-sm">Loading...</p>}
          {data && (
            <>
              <p className="text-sm text-[#73808c] mb-4">
                Showing <span className="font-mono-data">{data.entries.length}</span> of <span className="font-mono-data">{data.total}</span> entries
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#2a3138]">
                      <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Time</th>
                      <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Module</th>
                      <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Action</th>
                      <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Target</th>
                      <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Result</th>
                      <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Safety</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.entries.map((e, i) => (
                      <tr key={i} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                        <td className="py-2.5 px-3 text-xs text-[#73808c] font-mono-data whitespace-nowrap">{e.timestamp}</td>
                        <td className="py-2.5 px-3"><Badge variant="outline" className="text-[10px] font-mono-data">{e.module}</Badge></td>
                        <td className="py-2.5 px-3 text-[#a7b0b8]">{e.action}</td>
                        <td className="py-2.5 px-3 max-w-[200px] truncate text-[#73808c]">{e.target}</td>
                        <td className="py-2.5 px-3">
                          <Badge className={
                            e.result === "OK" ? "bg-[#22c55e]/15 text-[#22c55e] border border-[#22c55e]/25" :
                            e.result === "FAILED" ? "bg-[#ef4444]/15 text-[#ef4444] border border-[#ef4444]/25" :
                            "bg-[#73808c]/15 text-[#73808c] border border-[#73808c]/25"
                          }>{e.result}</Badge>
                        </td>
                        <td className="py-2.5 px-3 text-xs text-[#73808c]">{e.safety}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex justify-between mt-4">
                <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</Button>
                <Button size="sm" variant="outline" disabled={data.entries.length < limit} onClick={() => setOffset(offset + limit)}>Next</Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
