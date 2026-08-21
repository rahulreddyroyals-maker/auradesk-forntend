"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { Button } from "@/components/ui/button";
import { Card, Input, Label } from "@/components/ui/primitives";
import { apiGet, apiPatch } from "@/lib/api-client";
import { Check } from "lucide-react";

interface Clinic {
  id: string;
  name: string;
  slug: string;
  phone_number: string | null;
  address: string | null;
  timezone: string;
}

export default function SettingsPage() {
  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiGet<Clinic>("/clinic")
      .then(setClinic)
      .catch(() => setError("Couldn't load clinic settings. Is the backend running?"));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clinic) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await apiPatch<Clinic>("/clinic", {
        name: clinic.name,
        phone_number: clinic.phone_number,
        address: clinic.address,
        timezone: clinic.timezone,
      });
      setClinic(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Couldn't save changes. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <TopBar title="Settings" />
      <main className="flex flex-1 flex-col p-8 gap-6 max-w-xl">
        <p className="text-sm text-muted-foreground">
          Your clinic's basic details. The phone number here must match your Twilio number exactly —
          it's how inbound calls and texts get routed to your AI Employee.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {!clinic && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {clinic && (
          <Card>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <Label htmlFor="name">Clinic name</Label>
                <Input
                  id="name"
                  required
                  value={clinic.name}
                  onChange={(e) => setClinic({ ...clinic, name: e.target.value })}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="phone">Phone number (Twilio)</Label>
                <Input
                  id="phone"
                  value={clinic.phone_number ?? ""}
                  onChange={(e) => setClinic({ ...clinic, phone_number: e.target.value })}
                  placeholder="+15551234567"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="address">Address</Label>
                <Input
                  id="address"
                  value={clinic.address ?? ""}
                  onChange={(e) => setClinic({ ...clinic, address: e.target.value })}
                  placeholder="123 Main St, Springfield, IL"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="timezone">Timezone</Label>
                <Input
                  id="timezone"
                  required
                  value={clinic.timezone}
                  onChange={(e) => setClinic({ ...clinic, timezone: e.target.value })}
                  placeholder="America/New_York"
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
      </main>
    </>
  );
}
