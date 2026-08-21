"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { Card, Input, Label } from "@/components/ui/primitives";
import { apiGet, apiPost, apiPatch, apiDelete } from "@/lib/api-client";
import { Sparkles, Plus, Trash2, Pencil, Check, X } from "lucide-react";

interface Service {
  id: string;
  name: string;
  category: string | null;
  duration_minutes: number;
  price_cents: number | null;
  description: string | null;
  active: boolean;
}

function formatPrice(cents: number | null) {
  if (cents === null) return "—";
  return `$${(cents / 100).toFixed(0)}`;
}

export default function ServicesPage() {
  const [services, setServices] = useState<Service[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", category: "", duration_minutes: 30, price_cents: "" });
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setServices(await apiGet<Service[]>("/services"));
    } catch {
      setError("Couldn't load services. Is the backend running?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function startCreate() {
    setEditingId(null);
    setForm({ name: "", category: "", duration_minutes: 30, price_cents: "" });
    setShowForm(true);
  }

  function startEdit(service: Service) {
    setEditingId(service.id);
    setForm({
      name: service.name,
      category: service.category ?? "",
      duration_minutes: service.duration_minutes,
      price_cents: service.price_cents !== null ? String(service.price_cents / 100) : "",
    });
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    const payload = {
      name: form.name,
      category: form.category || null,
      duration_minutes: Number(form.duration_minutes),
      price_cents: form.price_cents ? Math.round(Number(form.price_cents) * 100) : null,
    };
    try {
      if (editingId) {
        await apiPatch(`/services/${editingId}`, payload);
      } else {
        await apiPost("/services", payload);
      }
      setShowForm(false);
      await load();
    } catch {
      setError("Couldn't save that service. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await apiDelete(`/services/${id}`);
      await load();
    } catch {
      setError("Couldn't delete that service.");
    }
  }

  return (
    <>
      <TopBar title="Services" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground max-w-lg">
            The treatments your AI Employee can book — Botox, fillers, laser, and anything else you offer.
          </p>
          {!showForm && (
            <Button onClick={startCreate}>
              <Plus className="h-4 w-4" /> Add service
            </Button>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {showForm && (
          <Card>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    required
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Botox"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="category">Category</Label>
                  <Input
                    id="category"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    placeholder="Injectables"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="duration">Duration (minutes)</Label>
                  <Input
                    id="duration"
                    type="number"
                    min={5}
                    max={480}
                    required
                    value={form.duration_minutes}
                    onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="price">Price (USD)</Label>
                  <Input
                    id="price"
                    type="number"
                    min={0}
                    step="0.01"
                    value={form.price_cents}
                    onChange={(e) => setForm({ ...form, price_cents: e.target.value })}
                    placeholder="350"
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

        {services === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {services !== null && services.length === 0 && (
          <EmptyState
            icon={Sparkles}
            title="No services yet"
            description="Add the treatments you offer so your AI Employee knows what it can book."
          />
        )}

        {services !== null && services.length > 0 && (
          <div className="grid grid-cols-2 gap-3">
            {services.map((service) => (
              <Card key={service.id} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-sm">{service.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {service.category ? `${service.category} · ` : ""}
                    {service.duration_minutes} min · {formatPrice(service.price_cents)}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button onClick={() => startEdit(service)} className="rounded-full p-2 hover:bg-muted" aria-label="Edit">
                    <Pencil className="h-4 w-4 text-muted-foreground" />
                  </button>
                  <button onClick={() => handleDelete(service.id)} className="rounded-full p-2 hover:bg-muted" aria-label="Delete">
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
