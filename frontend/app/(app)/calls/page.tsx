"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Card } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { Phone } from "lucide-react";

interface ConversationSummary {
  id: string;
  channel: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  ai_handled: boolean;
  outcome: string | null;
  patient_name: string | null;
}

const statusStyles: Record<string, string> = {
  active: "bg-blue-500/10 text-blue-700",
  escalated: "bg-amber-500/10 text-amber-700",
  resolved: "bg-green-500/10 text-green-700",
  abandoned: "bg-muted text-muted-foreground",
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function durationLabel(start: string, end: string | null) {
  if (!end) return "In progress";
  const seconds = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000);
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function CallsPage() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ConversationSummary[]>("/conversations")
      .then((all) => setConversations(all.filter((c) => c.channel === "voice")))
      .catch(() => setError("Couldn't load calls. Is the backend running?"));
  }, []);

  return (
    <>
      <TopBar title="Calls" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <p className="text-sm text-muted-foreground max-w-lg">
          Inbound calls your AI Employee has answered. Set up Twilio Voice in Integrations to start
          receiving real calls.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {conversations === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {conversations !== null && conversations.length === 0 && (
          <EmptyState
            icon={Phone}
            title="No calls yet"
            description="Once your Twilio Voice number is connected, answered calls will appear here."
          />
        )}

        {conversations !== null && conversations.length > 0 && (
          <div className="space-y-2">
            {conversations.map((c) => (
              <Card key={c.id} className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-aura-gold-500/10">
                    <Phone className="h-4 w-4 text-aura-gold-700" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{c.patient_name || "Unknown caller"}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatTime(c.started_at)} · {durationLabel(c.started_at, c.ended_at)}
                      {c.ai_handled ? " · Handled by AI" : ""}
                    </p>
                  </div>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${statusStyles[c.status] ?? "bg-muted text-muted-foreground"}`}
                >
                  {c.status}
                </span>
              </Card>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
