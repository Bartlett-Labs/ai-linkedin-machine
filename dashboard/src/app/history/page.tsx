"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/hooks/use-api";
import { getHistory, exportHistoryCsv } from "@/lib/api";
import type { HistoryResponse } from "@/lib/api";
import { Clock, Download } from "lucide-react";

export default function HistoryPage() {
  const [offset, setOffset] = useState(0);
  const [actionFilter, setActionFilter] = useState("");
  const limit = 50;
  const { data, loading, refetch } = useApi<HistoryResponse>(
    () => getHistory({ limit, offset, action: actionFilter || undefined }), [offset, actionFilter]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Clock className="h-6 w-6" />Activity History</h2>
        <a href={exportHistoryCsv()} target="_blank" rel="noopener noreferrer">
          <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" />Export CSV</Button>
        </a>
      </div>
      <div className="flex gap-2">
        <Input placeholder="Filter by action..." value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setOffset(0); }} className="max-w-xs" />
        <Button variant="outline" size="sm" onClick={refetch}>Search</Button>
      </div>
      <Card>
        <CardContent className="pt-6">
          {loading && <p className="text-muted-foreground">Loading...</p>}
          {data && (
            <>
              <p className="text-sm text-muted-foreground mb-4">Showing {data.entries.length} of {data.total} entries</p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b text-left"><th className="py-2">Time</th><th>Module</th><th>Action</th><th>Target</th><th>Result</th><th>Safety</th></tr></thead>
                  <tbody>
                    {data.entries.map((e, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2 text-xs text-muted-foreground whitespace-nowrap">{e.timestamp}</td>
                        <td><Badge variant="outline" className="text-xs">{e.module}</Badge></td>
                        <td>{e.action}</td>
                        <td className="max-w-[200px] truncate">{e.target}</td>
                        <td><Badge className={e.result === "OK" ? "bg-green-500" : e.result === "FAILED" ? "bg-red-500" : "bg-gray-500"}>{e.result}</Badge></td>
                        <td className="text-xs">{e.safety}</td>
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
