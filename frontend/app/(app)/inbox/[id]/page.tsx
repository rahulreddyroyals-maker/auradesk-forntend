"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { TopBar } from "@/components/shared/top-bar";
import { Card } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { ArrowLeft, Phone, MessageSquare, MessagesSquare, Facebook, Instagram } from "lucide-react";

interface Message {
  id: string;
  role: string;
  channel: string;
  content: string;
  created_at: string;
}

interface ConversationDetail {
  id: string;
  channel: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  ai_handled: boolean;
  outcome: string | null;
  patient_name: string | null;
  messages: Message[];
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

const roleBubbleStyles: Record<string, string> = {
  patient: "bg-card border border-border self-start",
  ai: "bg-aura-gold-500/10 border border-aura-gold-500/30 self-end",
  staff: "bg-blue-500/10 border border-blue-500/30 self-end",
  system: "bg-muted text-muted-foreground self-center text-xs italic",
};

const roleLabels: Record<string, string> = {
  patient: "Patient",
  ai: "Aura (AI)",
  staff: "Staff",
  system: "System",
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function ConversationDetailPage() {
  const params = useParams<{ id: string }>();
  const [conv, setConv] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    apiGet<ConversationDetail>(`/conversations/${params.id}`)
      .then(setConv)
      .catch(() => setError("Couldn't load this conversation."));
  }, [params?.id]);

  const Icon = conv ? channelIcons[conv.channel] ?? MessagesSquare : MessagesSquare;

  return (
    <>
      <TopBar title="Conversation" />
      <main className="flex flex-1 flex-col p-8 gap-6 max-w-2xl mx-auto w-full">
        <Link
          href="/inbox"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to inbox
        </Link>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {!conv && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {conv && (
          <>
            <Card className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-aura-gold-500/10">
                  <Icon className="h-4 w-4 text-aura-gold-700" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">{conv.patient_name || "Unknown patient"}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {conv.channel.replace("_", " ")} · {formatTime(conv.started_at)}
                    {conv.outcome ? ` · Outcome: ${conv.outcome.replace("_", " ")}` : ""}
                  </p>
                </div>
              </div>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${statusStyles[conv.status] ?? "bg-muted text-muted-foreground"}`}
              >
                {conv.status}
              </span>
            </Card>

            <div className="flex flex-col gap-3">
              {conv.messages.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">No messages in this conversation.</p>
              )}
              {conv.messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex flex-col max-w-[80%] rounded-2xl px-4 py-2.5 ${roleBubbleStyles[m.role] ?? "bg-card border border-border self-start"}`}
                >
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="text-[11px] font-medium text-muted-foreground">
                      {roleLabels[m.role] ?? m.role}
                    </span>
                    <span className="text-[11px] text-muted-foreground shrink-0">{formatTime(m.created_at)}</span>
                  </div>
                  <p className="text-sm mt-0.5 whitespace-pre-wrap">{m.content}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
