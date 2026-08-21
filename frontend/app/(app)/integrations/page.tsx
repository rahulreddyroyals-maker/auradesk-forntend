"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { Button } from "@/components/ui/button";
import { Card, Input, Label } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { Facebook, Instagram, Check, Phone } from "lucide-react";

interface Integration {
  id: string;
  type: string;
  status: string;
  connected_at: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8081/api/v1";

async function authedPut(path: string, body: unknown) {
  const { createClient } = await import("@/lib/supabase/client");
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`);
  return res.json();
}

function ChannelCard({
  icon: Icon,
  title,
  description,
  type,
  connected,
  onSaved,
}: {
  icon: typeof Facebook;
  title: string;
  description: string;
  type: "messenger" | "instagram";
  connected: boolean;
  onSaved: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [pageId, setPageId] = useState("");
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await authedPut("/integrations", { type, page_id: pageId, page_access_token: token });
      setShowForm(false);
      onSaved();
    } catch {
      setError("Couldn't save. Check your Page ID and access token.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-aura-gold-500/10">
            <Icon className="h-5 w-5 text-aura-gold-700" />
          </div>
          <div>
            <p className="font-medium text-sm">{title}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
          </div>
        </div>
        {connected ? (
          <span className="flex items-center gap-1 rounded-full bg-green-500/10 px-2.5 py-0.5 text-[11px] font-medium text-green-700">
            <Check className="h-3 w-3" /> Connected
          </span>
        ) : (
          <Button variant="secondary" onClick={() => setShowForm(!showForm)}>
            Connect
          </Button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSave} className="mt-4 space-y-3 border-t border-border pt-4">
          <div className="space-y-1.5">
            <Label htmlFor={`${type}-page-id`}>Page ID</Label>
            <Input id={`${type}-page-id`} required value={pageId} onChange={(e) => setPageId(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={`${type}-token`}>Page Access Token</Label>
            <Input id={`${type}-token`} required type="password" value={token} onChange={(e) => setToken(e.target.value)} />
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </form>
      )}
    </Card>
  );
}

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);

  async function load() {
    try {
      setIntegrations(await apiGet<Integration[]>("/integrations"));
    } catch {
      // fine to show everything as "not connected" if this fails
    }
  }

  useEffect(() => {
    load();
  }, []);

  const isConnected = (type: string) => integrations.some((i) => i.type === type && i.status === "connected");

  return (
    <>
      <TopBar title="Integrations" />
      <main className="flex flex-1 flex-col p-8 gap-6 max-w-2xl">
        <p className="text-sm text-muted-foreground">
          Connect the channels your AI Employee should handle. SMS and Voice are configured via
          Twilio in Settings; Messenger and Instagram are configured here.
        </p>

        <Card className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-aura-gold-500/10">
            <Phone className="h-5 w-5 text-aura-gold-700" />
          </div>
          <div>
            <p className="font-medium text-sm">SMS &amp; Voice (Twilio)</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Set your clinic's phone number in Settings, and point your Twilio number's webhooks at
              your backend.
            </p>
          </div>
        </Card>

        <ChannelCard
          icon={Facebook}
          title="Messenger"
          description="Requires a Facebook Page connected to your Meta app, with a Page Access Token."
          type="messenger"
          connected={isConnected("messenger")}
          onSaved={load}
        />
        <ChannelCard
          icon={Instagram}
          title="Instagram"
          description="Requires an Instagram Business account linked to the same Facebook Page."
          type="instagram"
          connected={isConnected("instagram")}
          onSaved={load}
        />
      </main>
    </>
  );
}
