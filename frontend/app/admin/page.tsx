"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiGet, apiPatch } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { Logo } from "@/components/shared/logo";

interface Subscription {
  status: string;
  plan: string | null;
  current_period_end: string | null;
}

interface ClinicAdmin {
  id: string;
  name: string;
  slug: string;
  status: string;
  created_at: string;
  staff_count: number;
  service_count: number;
  subscription: Subscription | null;
}

const clinicStatusStyles: Record<string, string> = {
  trial: "bg-blue-500/10 text-blue-700",
  active: "bg-green-500/10 text-green-700",
  paused: "bg-amber-500/10 text-amber-700",
  canceled: "bg-muted text-muted-foreground",
};

const subStatusStyles: Record<string, string> = {
  active: "bg-green-500/10 text-green-700",
  past_due: "bg-amber-500/10 text-amber-700",
  canceled: "bg-red-500/10 text-red-700",
  none: "bg-muted text-muted-foreground",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export default function PlatformAdminPage() {
  const { session, loading: authLoading } = useAuth();
  const router = useRouter();
  const [clinics, setClinics] = useState<ClinicAdmin[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !session) {
      router.replace("/login");
    }
  }, [authLoading, session, router]);

  function load() {
    apiGet<ClinicAdmin[]>("/admin/clinics")
      .then(setClinics)
      .catch((e: Error) => {
        setError(
          e.message.includes("403")
            ? "This account isn't set up as a platform admin."
            : e.message.includes("503")
            ? "Platform admin isn't configured on this server yet (PLATFORM_ADMIN_EMAILS unset)."
            : "Couldn't load clinics."
        );
      });
  }

  useEffect(() => {
    if (session) load();
  }, [session]);

  async function toggleClinicStatus(clinic: ClinicAdmin) {
    const next = clinic.status === "paused" ? "active" : "paused";
    setBusyId(clinic.id);
    try {
      await apiPatch(`/admin/clinics/${clinic.id}/status`, { status: next });
      load();
    } catch {
      setError("Couldn't update that clinic's status.");
    } finally {
      setBusyId(null);
    }
  }

  async function setSubscriptionStatus(clinic: ClinicAdmin, status: string) {
    setBusyId(clinic.id);
    try {
      await apiPatch(`/admin/clinics/${clinic.id}/subscription`, { status });
      load();
    } catch {
      setError("Couldn't update that clinic's subscription.");
    } finally {
      setBusyId(null);
    }
  }

  if (authLoading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-6 w-6 animate-pulse rounded-full bg-aura-gold-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <Logo href="/" size={28} />
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:underline">
          Back to app
        </Link>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Platform admin</h1>
        <p className="mt-1 text-sm text-muted-foreground">Every clinic on AuraDesk — status, plan, and billing.</p>

        {error && (
          <Card className="mt-6">
            <p className="text-sm text-red-600">{error}</p>
          </Card>
        )}

        {!error && clinics === null && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}

        {!error && clinics !== null && clinics.length === 0 && (
          <Card className="mt-6">
            <p className="text-sm text-muted-foreground">No clinics have signed up yet.</p>
          </Card>
        )}

        {!error && clinics !== null && clinics.length > 0 && (
          <div className="mt-6 space-y-3">
            {clinics.map((c) => (
              <Card key={c.id} className="flex flex-wrap items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{c.name}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${clinicStatusStyles[c.status] ?? "bg-muted"}`}
                    >
                      {c.status}
                    </span>
                    {c.subscription && (
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${subStatusStyles[c.subscription.status] ?? "bg-muted"}`}
                      >
                        {c.subscription.plan ? `${c.subscription.plan} · ` : ""}
                        {c.subscription.status.replace("_", " ")}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {c.slug} · {c.staff_count} staff · {c.service_count} services · signed up{" "}
                    {formatDate(c.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Button
                    variant="secondary"
                    className="px-3 py-1.5 text-xs"
                    disabled={busyId === c.id}
                    onClick={() => toggleClinicStatus(c)}
                  >
                    {c.status === "paused" ? "Reactivate" : "Suspend"}
                  </Button>
                  <Button
                    variant="secondary"
                    className="px-3 py-1.5 text-xs"
                    disabled={busyId === c.id}
                    onClick={() => setSubscriptionStatus(c, c.subscription?.status === "active" ? "past_due" : "active")}
                  >
                    Mark {c.subscription?.status === "active" ? "past due" : "active"}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
