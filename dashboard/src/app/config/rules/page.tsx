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
        <div>
          <Label>Condition Type</Label>
          <Select value={conditionType} onValueChange={setConditionType}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{CONDITION_TYPES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <Label>Action</Label>
          <Select value={action} onValueChange={setAction}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>{ACTIONS.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>
      <div>
        <Label>Trigger</Label>
        <Input value={trigger} onChange={e => setTrigger(e.target.value)} placeholder="e.g. 'hire' or 'looking for work'" />
      </div>
      <div>
        <Label>Notes</Label>
        <Input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional notes..." />
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !trigger.trim()}>{saving ? "Saving..." : "Create"}</Button>
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
      <div>
        <Label>Term / Phrase</Label>
        <Input value={term} onChange={e => setTerm(e.target.value)} placeholder="e.g. 'hire me'" />
      </div>
      <div>
        <Label>Response</Label>
        <Select value={response} onValueChange={setResponse}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{RESPONSES.map(r => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={save} disabled={saving || !term.trim()}>{saving ? "Saving..." : "Create"}</Button>
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
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2"><Shield className="h-6 w-6" />Rules & Safety</h2>
      <Tabs defaultValue="rules">
        <TabsList><TabsTrigger value="rules">Reply Rules</TabsTrigger><TabsTrigger value="safety">Safety Terms</TabsTrigger></TabsList>
        <TabsContent value="rules" className="mt-4 space-y-4">
          <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
            <Button onClick={() => setRuleDialogOpen(true)} className="flex items-center gap-2"><Plus className="h-4 w-4" />Add Rule</Button>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>New Reply Rule</DialogTitle></DialogHeader>
              <ReplyRuleForm onSave={rules.refetch} onClose={() => setRuleDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          <table className="w-full text-sm"><thead><tr className="border-b"><th className="text-left py-2">Type</th><th>Trigger</th><th>Action</th><th>Notes</th><th></th></tr></thead>
            <tbody>{rules.data?.map((r, i) => (
              <tr key={i} className="border-b last:border-0"><td className="py-2">{r.condition_type}</td><td>{r.trigger}</td>
                <td><Badge className={r.action === "BLOCK" ? "bg-red-500" : r.action === "REPLY" ? "bg-green-500" : "bg-gray-500"}>{r.action}</Badge></td>
                <td className="text-xs text-muted-foreground">{r.notes}</td>
                <td><Button variant="ghost" size="sm" onClick={() => deleteReplyRule(r.trigger).then(rules.refetch)}><Trash2 className="h-4 w-4" /></Button></td></tr>
            ))}</tbody></table>
        </TabsContent>
        <TabsContent value="safety" className="mt-4 space-y-4">
          <Dialog open={safetyDialogOpen} onOpenChange={setSafetyDialogOpen}>
            <Button onClick={() => setSafetyDialogOpen(true)} className="flex items-center gap-2"><Plus className="h-4 w-4" />Add Safety Term</Button>
            <DialogContent className="max-w-md">
              <DialogHeader><DialogTitle>New Safety Term</DialogTitle></DialogHeader>
              <SafetyTermForm onSave={safety.refetch} onClose={() => setSafetyDialogOpen(false)} />
            </DialogContent>
          </Dialog>
          <table className="w-full text-sm"><thead><tr className="border-b"><th className="text-left py-2">Term</th><th>Response</th><th></th></tr></thead>
            <tbody>{safety.data?.map((s, i) => (
              <tr key={i} className="border-b last:border-0"><td className="py-2">{s.term}</td>
                <td><Badge className={s.response === "BLOCK" ? "bg-red-500" : "bg-yellow-500"}>{s.response}</Badge></td>
                <td><Button variant="ghost" size="sm" onClick={() => deleteSafetyTerm(s.term).then(safety.refetch)}><Trash2 className="h-4 w-4" /></Button></td></tr>
            ))}</tbody></table>
        </TabsContent>
      </Tabs>
    </div>
  );
}
