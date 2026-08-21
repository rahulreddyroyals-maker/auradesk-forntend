"use client";

import { useEffect, useRef, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { Button } from "@/components/ui/button";
import { Card, Input, Label, Textarea } from "@/components/ui/primitives";
import { apiGet, apiPatch, apiPost } from "@/lib/api-client";
import { Check, Send, AlertTriangle } from "lucide-react";

interface AIEmployee {
  id: string;
  name: string;
  voice_id: string | null;
  personality_prompt: string;
  status: "active" | "paused";
}

interface ChatTurn {
  role: "patient" | "ai";
  content: string;
  escalated?: boolean;
}

export default function AIEmployeePage() {
  const [employee, setEmployee] = useState<AIEmployee | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiGet<AIEmployee>("/ai-employee")
      .then(setEmployee)
      .catch(() => setError("Couldn't load your AI Employee config. Is the backend running?"));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!employee) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await apiPatch<AIEmployee>("/ai-employee", {
        name: employee.name,
        personality_prompt: employee.personality_prompt,
        status: employee.status,
      });
      setEmployee(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Couldn't save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function sendTestMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || sending) return;
    const message = draft.trim();
    setDraft("");
    setChatError(null);
    setTurns((t) => [...t, { role: "patient", content: message }]);
    setSending(true);
    try {
      const res = await apiPost<{ conversation_id: string; reply: string; escalated: boolean }>(
        "/ai-employee/test-message",
        { message, conversation_id: conversationId }
      );
      setConversationId(res.conversation_id);
      setTurns((t) => [...t, { role: "ai", content: res.reply, escalated: res.escalated }]);
    } catch {
      setChatError("Couldn't reach your AI Employee. Check that GROQ_API_KEY is set and the backend is running.");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <TopBar title="AI Employee" />
      <main className="flex flex-1 flex-col p-8 gap-6 max-w-5xl">
        <p className="text-sm text-muted-foreground">
          Configure how your AI Employee introduces itself and behaves, then try it out on the right —
          it's the exact same brain that will answer real calls and messages.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid grid-cols-2 gap-6 items-start">
          {!employee && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

          {employee && (
            <Card>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-1.5">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    required
                    value={employee.name}
                    onChange={(e) => setEmployee({ ...employee, name: e.target.value })}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="status">Status</Label>
                  <select
                    id="status"
                    value={employee.status}
                    onChange={(e) =>
                      setEmployee({ ...employee, status: e.target.value as "active" | "paused" })
                    }
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-aura-gold-500/40"
                  >
                    <option value="active">Active — answering conversations</option>
                    <option value="paused">Paused — staff handle everything</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="personality">Personality &amp; tone</Label>
                  <Textarea
                    id="personality"
                    rows={6}
                    value={employee.personality_prompt}
                    onChange={(e) => setEmployee({ ...employee, personality_prompt: e.target.value })}
                    placeholder="Warm, professional, and concise. Speaks like an experienced med spa front desk coordinator..."
                  />
                </div>

                <div className="flex items-center gap-3">
                  <Button type="submit" disabled={saving}>
                    <Check className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
                  </Button>
                  {saved && <span className="text-xs text-muted-foreground">Saved</span>}
                </div>
              </form>
            </Card>
          )}

          <Card className="flex flex-col h-[520px] p-0 overflow-hidden">
            <div className="border-b border-border px-4 py-3">
              <p className="text-sm font-medium">Test your AI Employee</p>
              <p className="text-xs text-muted-foreground">
                Chat as a patient would — this calls the real orchestrator.
              </p>
            </div>

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {turns.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Try: &quot;How much does Botox cost?&quot; or &quot;Can I book an appointment?&quot;
                </p>
              )}
              {turns.map((turn, i) => (
                <div key={i} className={turn.role === "patient" ? "flex justify-end" : "flex justify-start"}>
                  <div
                    className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${
                      turn.role === "patient"
                        ? "bg-aura-ink-900 text-white dark:bg-aura-gold-500 dark:text-aura-ink-900"
                        : "bg-muted"
                    }`}
                  >
                    {turn.content}
                    {turn.escalated && (
                      <div className="mt-1.5 flex items-center gap-1 text-[11px] text-amber-600">
                        <AlertTriangle className="h-3 w-3" /> Escalated to staff
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {sending && <p className="text-xs text-muted-foreground">Thinking…</p>}
            </div>

            {chatError && <p className="px-4 pb-1 text-xs text-red-600">{chatError}</p>}

            <form onSubmit={sendTestMessage} className="flex items-center gap-2 border-t border-border p-3">
              <Input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Type a message…"
                disabled={sending}
              />
              <Button type="submit" disabled={sending || !draft.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </Card>
        </div>
      </main>
    </>
  );
}
