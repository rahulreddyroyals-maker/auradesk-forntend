"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Card } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { ScrollText } from "lucide-react";

interface LogEntry {
  id: string;
  conversation_id: string;
  channel: string;
  created_at: string;
  tool: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<LogEntry[]>("/logs")
      .then(setLogs)
      .catch(() => setError("Couldn't load logs. Is the backend running?"));
  }, []);

  return (
    <>
      <TopBar title="Logs" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <p className="text-sm text-muted-foreground max-w-lg">
          Every tool your AI Employee has used — knowledge base lookups, bookings, escalations — with
          what it looked up and what it did.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {logs === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {logs !== null && logs.length === 0 && (
          <EmptyState
            icon={ScrollText}
            title="No activity yet"
            description="Once your AI Employee starts using tools — looking things up, booking appointments — it'll show up here."
          />
        )}

        {logs !== null && logs.length > 0 && (
          <div className="space-y-2">
            {logs.map((log) => (
              <Card key={`${log.id}-${log.tool}`} className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-aura-gold-500/10 px-2.5 py-0.5 text-[11px] font-medium text-aura-gold-700">
                      {log.tool}
                    </span>
                    <span className="text-xs text-muted-foreground capitalize">{log.channel}</span>
                  </div>
                  <pre className="mt-1.5 whitespace-pre-wrap text-xs text-muted-foreground font-mono">
                    {JSON.stringify(log.arguments)}
                  </pre>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">{formatTime(log.created_at)}</span>
              </Card>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
