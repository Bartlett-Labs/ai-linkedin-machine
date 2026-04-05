"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApi } from "@/hooks/use-api";
import { getReplyRules, createReplyRule, deleteReplyRule, getSafetyTerms, createSafetyTerm, deleteSafetyTerm } from "@/lib/api";
import type { ReplyRule, SafetyTerm } from "@/lib/api";
import { Shield, Trash2, Plus } from "lucide-react";

const CONDITION_TYPES = ["keyword", "phrase", "regex"];
const ACTIONS = ["BLOCK", "REPLY", "IGNORE"];
const RESPONSES = ["BLOCK", "MASK"];

function ReplyRuleForm({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [conditionType, setConditionType] = useState("keyword");
  const [trigger, setTrigger] = useState("");
  const [action, setAction] = useState("REPLY");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await createReplyRule({ condition_type: conditionType, trigger, action, notes: notes || null });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Condition Type</Label>
          <Select value={conditionType} onValueChange={setConditionType}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CONDITION_TYPES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Action</Label>
          <Select value={action} onValueChange={setAction}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{ACTIONS.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Trigger</Label><Input value={trigger} onChange={e => setTrigger(e.target.value)} placeholder="e.g. 'hire' or 'looking for work'" /></div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Notes</Label><Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." /></div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !trigger.trim()} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : "Create"}</Button>
      </div>
    </div>
  );
}

function SafetyTermForm({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  const [term, setTerm] = useState("");
  const [response, setResponse] = useState("BLOCK");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    await createSafetyTerm({ term, response });
    setSaving(false);
    onSave();
    onClose();
  };

  return (
    <div className="space-y-4">
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Term / Phrase</Label><Input value={term} onChange={e => setTerm(e.target.value)} placeholder="e.g. 'hire me'" /></div>
      <div><Label className="text-xs text-[#73808c] uppercase tracking-wider">Response</Label>
        <Select value={response} onValueChange={setResponse}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{RESPONSES.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !term.trim()} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee]">{saving ? "Saving..." : "Create"}</Button>
      </div>
    </div>
  );
}

export default function RulesConfigPage() {
  const rules = useApi<ReplyRule[]>(getReplyRules);
  const safety = useApi<SafetyTerm[]>(getSafetyTerms);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [safetyDialogOpen, setSafetyDialogOpen] = useState(false);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-2xl font-semibold flex items-center gap-2.5">
          <Shield className="h-5 w-5 text-[#06b6d4]" />Rules & Safety
        </h2>
        <p className="text-sm text-[#73808c] mt-1">Reply rules and safety term configuration</p>
      </div>
      <Tabs defaultValue="rules">
        <TabsList><TabsTrigger value="rules">Reply Rules</TabsTrigger><TabsTrigger value="safety">Safety Terms</TabsTrigger></TabsList>
        <TabsContent value="rules" className="mt-4 space-y-4">
          <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
            <Button onClick={() => setRuleDialogOpen(true)} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Rule</Button>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>New Reply Rule</DialogTitle></DialogHeader>
              <ReplyRuleForm onSave={rules.refetch} onClose={() => setRuleDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#2a3138]">
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Type</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Trigger</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Action</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Notes</th>
                    <th className="py-2.5 px-3"></th>
                  </tr>
                </thead>
                <tbody>{rules.data?.map((r, i) => (
                  <tr key={i} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                    <td className="py-2.5 px-3 font-mono-data text-xs text-[#a7b0b8]">{r.condition_type}</td>
                    <td className="py-2.5 px-3 text-[#a7b0b8]">{r.trigger}</td>
                    <td className="py-2.5 px-3">
                      <Badge className={`text-[10px] border ${
                        r.action === "BLOCK" ? "bg-[#ef4444]/15 text-[#ef4444] border-[#ef4444]/25" :
                        r.action === "REPLY" ? "bg-[#22c55e]/15 text-[#22c55e] border-[#22c55e]/25" :
                        "bg-[#73808c]/15 text-[#73808c] border-[#73808c]/25"
                      }`}>{r.action}</Badge>
                    </td>
                    <td className="py-2.5 px-3 text-xs text-[#73808c]">{r.notes}</td>
                    <td className="py-2.5 px-3"><Button variant="ghost" size="sm" className="text-[#73808c] hover:text-[#ef4444]" onClick={() => deleteReplyRule(r.trigger).then(rules.refetch)}><Trash2 className="h-4 w-4" /></Button></td>
                  </tr>
                ))}</tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="safety" className="mt-4 space-y-4">
          <Dialog open={safetyDialogOpen} onOpenChange={setSafetyDialogOpen}>
            <Button onClick={() => setSafetyDialogOpen(true)} className="bg-[#06b6d4] text-[#090a0b] hover:bg-[#22d3ee] gap-1.5"><Plus className="h-3.5 w-3.5" />Add Safety Term</Button>
            <DialogContent className="max-w-md">
              <DialogHeader><DialogTitle>New Safety Term</DialogTitle></DialogHeader>
              <SafetyTermForm onSave={safety.refetch} onClose={() => setSafetyDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#2a3138]">
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Term</th>
                    <th className="text-left py-2.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-[#73808c]">Response</th>
                    <th className="py-2.5 px-3"></th>
                  </tr>
                </thead>
                <tbody>{safety.data?.map((s, i) => (
                  <tr key={i} className="border-b border-[#2a3138]/50 last:border-0 hover:bg-[#161a1d] transition-colors">
                    <td className="py-2.5 px-3 text-[#a7b0b8]">{s.term}</td>
                    <td className="py-2.5 px-3">
                      <Badge className={`text-[10px] border ${
                        s.response === "BLOCK" ? "bg-[#ef4444]/15 text-[#ef4444] border-[#ef4444]/25" :
                        "bg-[#f59e0b]/15 text-[#f59e0b] border-[#f59e0b]/25"
                      }`}>{s.response}</Badge>
                    </td>
                    <td className="py-2.5 px-3"><Button variant="ghost" size="sm" className="text-[#73808c] hover:text-[#ef4444]" onClick={() => deleteSafetyTerm(s.term).then(safety.refetch)}><Trash2 className="h-4 w-4" /></Button></td>
                  </tr>
                ))}</tbody>
              </table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
