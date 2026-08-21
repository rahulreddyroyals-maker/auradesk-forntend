"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Card, Input, Label } from "@/components/ui/primitives";
import { apiGet, apiPost, apiDelete } from "@/lib/api-client";
import { Users, Plus, Trash2, Check, X } from "lucide-react";

interface StaffMember {
  id: string;
  name: string;
  role: string;
  phone: string | null;
  email: string | null;
}

const roleStyles: Record<string, string> = {
  owner: "bg-aura-gold-500/10 text-aura-gold-700",
  admin: "bg-blue-500/10 text-blue-700",
  front_desk: "bg-muted text-muted-foreground",
};

export default function TeamPage() {
  const [team, setTeam] = useState<StaffMember[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "front_desk" });
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setTeam(await apiGet<StaffMember[]>("/team"));
    } catch {
      setError("Couldn't load your team. Is the backend running?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await apiPost("/team/invite", form);
      setForm({ name: "", email: "", role: "front_desk" });
      setShowForm(false);
      await load();
    } catch {
      setError("Couldn't send that invite — the email may already be registered.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(id: string) {
    try {
      await apiDelete(`/team/${id}`);
      await load();
    } catch {
      setError("Couldn't remove that team member.");
    }
  }

  return (
    <>
      <TopBar title="Team" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground max-w-lg">
            Invite staff to your AuraDesk dashboard — they'll get an email to set their password.
          </p>
          {!showForm && (
            <Button onClick={() => setShowForm(true)}>
              <Plus className="h-4 w-4" /> Invite
            </Button>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {showForm && (
          <Card>
            <form onSubmit={handleInvite} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="role">Role</Label>
                  <select
                    id="role"
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                    className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-aura-gold-500/40"
                  >
                    <option value="front_desk">Front desk</option>
                    <option value="admin">Admin</option>
                    <option value="owner">Owner</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={saving}>
                  <Check className="h-4 w-4" /> {saving ? "Sending…" : "Send invite"}
                </Button>
                <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
                  <X className="h-4 w-4" /> Cancel
                </Button>
              </div>
            </form>
          </Card>
        )}

        {team === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {team !== null && team.length === 0 && (
          <EmptyState icon={Users} title="Just you so far" description="Invite staff to help manage conversations and appointments." />
        )}

        {team !== null && team.length > 0 && (
          <div className="space-y-2">
            {team.map((member) => (
              <Card key={member.id} className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{member.name}</p>
                  <p className="text-xs text-muted-foreground">{member.email}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${roleStyles[member.role] ?? "bg-muted"}`}>
                    {member.role.replace("_", " ")}
                  </span>
                  <button onClick={() => handleRemove(member.id)} className="rounded-full p-2 hover:bg-muted" aria-label="Remove">
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
