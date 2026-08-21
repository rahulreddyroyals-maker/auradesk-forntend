"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Card, Input, Label } from "@/components/ui/primitives";
import { apiGet, apiPost } from "@/lib/api-client";
import { UserCircle2, Plus, Check, X } from "lucide-react";

interface Patient {
  id: string;
  first_name: string;
  last_name: string | null;
  phone: string | null;
  email: string | null;
  lifecycle_stage: string;
  source_channel: string | null;
}

const stageStyles: Record<string, string> = {
  lead: "bg-blue-500/10 text-blue-700",
  patient: "bg-aura-gold-500/10 text-aura-gold-700",
  member: "bg-green-500/10 text-green-700",
};

export default function PatientsPage() {
  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", phone: "", email: "" });
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setPatients(await apiGet<Patient[]>("/patients"));
    } catch {
      setError("Couldn't load patients. Is the backend running?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await apiPost("/patients", {
        first_name: form.first_name,
        last_name: form.last_name || null,
        phone: form.phone || null,
        email: form.email || null,
      });
      setForm({ first_name: "", last_name: "", phone: "", email: "" });
      setShowForm(false);
      await load();
    } catch {
      setError("Couldn't save that patient. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <TopBar title="Patients" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground max-w-lg">
            Your patient and lead directory. Entries created by your AI Employee will show up here
            automatically once it's handling conversations.
          </p>
          {!showForm && (
            <Button onClick={() => setShowForm(true)}>
              <Plus className="h-4 w-4" /> Add patient
            </Button>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {showForm && (
          <Card>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="first_name">First name</Label>
                  <Input
                    id="first_name"
                    required
                    value={form.first_name}
                    onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="last_name">Last name</Label>
                  <Input
                    id="last_name"
                    value={form.last_name}
                    onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    placeholder="+1 555 000 1234"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>
                  <Check className="h-4 w-4" /> {saving ? "Saving…" : "Save"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  <X className="h-4 w-4" /> Cancel
                </Button>
              </div>
            </form>
          </Card>
        )}

        {patients === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {patients !== null && patients.length === 0 && (
          <EmptyState
            icon={UserCircle2}
            title="No patients yet"
            description="Your patient and lead directory will appear here."
          />
        )}

        {patients !== null && patients.length > 0 && (
          <Card className="p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Phone</th>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Stage</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <tr key={p.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 font-medium">
                      {p.first_name} {p.last_name ?? ""}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{p.phone ?? "—"}</td>
                    <td className="px-4 py-3 text-muted-foreground">{p.email ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${stageStyles[p.lifecycle_stage] ?? "bg-muted text-muted-foreground"}`}
                      >
                        {p.lifecycle_stage}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground capitalize">
                      {p.source_channel ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </main>
    </>
  );
}
