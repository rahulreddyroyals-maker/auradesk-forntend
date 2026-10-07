"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { Logo } from "@/components/shared/logo";

interface DemoInfo {
  clinic_name: string;
  login_email: string;
  login_password: string;
  note: string;
}

const FEATURES: { title: string; blurb: string }[] = [
  {
    title: "Dashboard",
    blurb: "Live counts of today's calls, texts, chats, bookings, and revenue — exactly what a clinic owner checks first.",
  },
  {
    title: "Conversations",
    blurb: "Real multi-channel threads — voice, SMS, web chat, Messenger, and Instagram — all in one inbox.",
  },
  {
    title: "Calls & SMS",
    blurb: "Full call and text history for the clinic's demo patients, with sentiment and call duration.",
  },
  {
    title: "Appointments",
    blurb: "Upcoming, completed, and no-show bookings, all tied to real services and patients.",
  },
  {
    title: "Escalations",
    blurb: "See exactly how and when Aura hands a sensitive conversation off to clinic staff.",
  },
  {
    title: "AI Employee & Knowledge Base",
    blurb: "The personality, escalation rules, and FAQ knowledge base that power every automated reply.",
  },
];

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard API can be unavailable (e.g. insecure context) — fail silently
    }
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border bg-background px-3 py-2">
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="truncate text-sm font-medium">{value}</div>
      </div>
      <Button variant="secondary" type="button" onClick={handleCopy} className="shrink-0 px-3 py-1.5 text-xs">
        {copied ? "Copied!" : "Copy"}
      </Button>
    </div>
  );
}

export default function DemoPage() {
  const [info, setInfo] = useState<DemoInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<DemoInfo>("/demo/info")
      .then(setInfo)
      .catch(() => setError("Couldn't load the demo details right now. Please try again shortly."));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-4">
        <Logo href="/" size={28} />
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12">
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">See AuraDesk in action</h1>
        <p className="mt-2 text-muted-foreground">
          This is a live, fully-populated demo clinic — not screenshots. Log in and explore the real dashboard,
          conversations, calls, appointments, and knowledge base exactly as a clinic owner would.
        </p>

        <Card className="mt-8">
          {error && <p className="text-sm text-red-600">{error}</p>}
          {!info && !error && <p className="text-sm text-muted-foreground">Loading demo details…</p>}
          {info && (
            <>
              <h2 className="text-lg font-medium">{info.clinic_name}</h2>
              <p className="mt-1 text-sm text-muted-foreground">{info.note}</p>
              <div className="mt-4 space-y-2">
                <CopyField label="Email" value={info.login_email} />
                <CopyField label="Password" value={info.login_password} />
              </div>
              <Link href="/login">
                <Button className="mt-5 w-full">Log in to the demo</Button>
              </Link>
            </>
          )}
        </Card>

        <div className="mt-12">
          <h2 className="text-lg font-medium">What you'll see inside</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <Card key={f.title} className="p-4">
                <h3 className="text-sm font-semibold">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.blurb}</p>
              </Card>
            ))}
          </div>
        </div>

        <p className="mt-10 text-center text-sm text-muted-foreground">
          Questions about bringing this to your own clinic?{" "}
          <Link href="/signup" className="text-aura-gold-600 hover:underline">
            Sign up for your own AuraDesk account
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
