"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { apiGet, apiPatch } from "@/lib/api-client";
import { Bell, Check, AlertTriangle } from "lucide-react";

interface EscalationItem {
  id: string;
  conversation_id: string;
  reason: string;
  urgency: string;
  resolved: boolean;
  created_at: string;
  patient_name: string | null;
}

const urgencyStyles: Record<string, string> = {
  low: "bg-muted text-muted-foreground",
  normal: "bg-blue-500/10 text-blue-700",
  high: "bg-amber-500/10 text-amber-700",
  urgent: "bg-red-500/10 text-red-700",
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function NotificationsPage() {
  const [escalations, setEscalations] = useState<EscalationItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  async function load() {
    try {
      setEscalations(await apiGet<EscalationItem[]>("/escalations"));
    } catch {
      setError("Couldn't load notifications. Is the backend running?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleResolve(id: string) {
    setResolvingId(id);
    try {
      await apiPatch(`/escalations/${id}/resolve`, {});
      await load();
    } catch {
      setError("Couldn't resolve that escalation.");
    } finally {
      setResolvingId(null);
    }
  }

  const unresolved = escalations?.filter((e) => !e.resolved) ?? [];
  const resolved = escalations?.filter((e) => e.resolved) ?? [];

  return (
    <>
      <TopBar title="Notifications" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <p className="text-sm text-muted-foreground max-w-lg">
          Conversations your AI Employee escalated to your team — urgent messages, complaints, or
          anything outside pricing/scheduling.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {escalations === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {escalations !== null && escalations.length === 0 && (
          <EmptyState
            icon={Bell}
            title="No escalations yet"
            description="When your AI Employee needs a human, it'll show up here — and your team gets a text."
          />
        )}

        {unresolved.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Needs attention
            </p>
            {unresolved.map((e) => (
              <Card key={e.id} className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-500/10">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{e.patient_name || "Unknown patient"}</p>
                    <p className="text-sm text-muted-foreground">{e.reason}</p>
                    <p className="text-xs text-muted-foreground mt-1">{formatTime(e.created_at)}</p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${urgencyStyles[e.urgency] ?? "bg-muted"}`}>
                    {e.urgency}
                  </span>
                  <Button variant="secondary" onClick={() => handleResolve(e.id)} disabled={resolvingId === e.id}>
                    <Check className="h-4 w-4" /> Resolve
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}

        {resolved.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Resolved</p>
            {resolved.map((e) => (
              <Card key={e.id} className="flex items-center justify-between gap-4 opacity-60">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{e.patient_name || "Unknown patient"}</p>
                  <p className="text-sm text-muted-foreground">{e.reason}</p>
                </div>
                <span className="text-xs text-muted-foreground">{formatTime(e.created_at)}</span>
              </Card>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
