"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Card } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { Inbox as InboxIcon, Phone, MessageSquare, MessagesSquare, Facebook, Instagram } from "lucide-react";

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

const channelIcons: Record<string, typeof Phone> = {
  voice: Phone,
  sms: MessageSquare,
  web_chat: MessagesSquare,
  messenger: Facebook,
  instagram: Instagram,
};

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

export default function InboxPage() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ConversationSummary[]>("/conversations")
      .then(setConversations)
      .catch(() => setError("Couldn't load your inbox. Is the backend running?"));
  }, []);

  return (
    <>
      <TopBar title="Inbox" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <p className="text-sm text-muted-foreground max-w-lg">
          Every conversation your AI Employee has had, across every channel, in one place.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {conversations === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {conversations !== null && conversations.length === 0 && (
          <EmptyState
            icon={InboxIcon}
            title="No conversations yet"
            description="Try talking to your AI Employee from the AI Employee page — conversations will show up here."
          />
        )}

        {conversations !== null && conversations.length > 0 && (
          <div className="space-y-2">
            {conversations.map((c) => {
              const Icon = channelIcons[c.channel] ?? MessagesSquare;
              return (
                <Link key={c.id} href={`/inbox/${c.id}`}>
                  <Card className="flex items-center justify-between gap-4 transition-colors hover:bg-muted/60 cursor-pointer">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-aura-gold-500/10">
                        <Icon className="h-4 w-4 text-aura-gold-700" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">
                          {c.patient_name || "Unknown patient"}
                        </p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {c.channel.replace("_", " ")} · {formatTime(c.started_at)}
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
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
