"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/primitives";
import { apiGet, apiPost } from "@/lib/api-client";
import { CreditCard } from "lucide-react";

interface Subscription {
  status: string;
  plan: string | null;
  current_period_end: string | null;
}

const statusStyles: Record<string, string> = {
  active: "bg-green-500/10 text-green-700",
  trialing: "bg-blue-500/10 text-blue-700",
  past_due: "bg-amber-500/10 text-amber-700",
  canceled: "bg-red-500/10 text-red-700",
  none: "bg-muted text-muted-foreground",
};

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    apiGet<Subscription>("/billing/subscription")
      .then(setSubscription)
      .catch(() => setError("Couldn't load billing status. Is the backend running?"));
  }, []);

  async function handleCheckout() {
    setRedirecting(true);
    setError(null);
    try {
      const res = await apiPost<{ checkout_url: string }>("/billing/checkout", {});
      window.location.href = res.checkout_url;
    } catch {
      setError("Couldn't start checkout. Stripe may not be fully configured yet.");
      setRedirecting(false);
    }
  }

  async function handlePortal() {
    setRedirecting(true);
    setError(null);
    try {
      const res = await apiPost<{ portal_url: string }>("/billing/portal", {});
      window.location.href = res.portal_url;
    } catch {
      setError("Couldn't open the billing portal.");
      setRedirecting(false);
    }
  }

  return (
    <>
      <TopBar title="Billing" />
      <main className="flex flex-1 flex-col p-8 gap-6 max-w-xl">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!subscription && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {subscription && (
          <Card className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-aura-gold-500/10">
                <CreditCard className="h-5 w-5 text-aura-gold-700" />
              </div>
              <div>
                <p className="font-medium text-sm">AuraDesk subscription</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {subscription.plan ? `Plan: ${subscription.plan}` : "No active plan yet"}
                </p>
                {subscription.current_period_end && (
                  <p className="text-xs text-muted-foreground">
                    Renews {new Date(subscription.current_period_end).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
            <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${statusStyles[subscription.status] ?? "bg-muted"}`}>
              {subscription.status.replace("_", " ")}
            </span>
          </Card>
        )}

        {subscription && subscription.status === "none" && (
          <Button onClick={handleCheckout} disabled={redirecting}>
            {redirecting ? "Redirecting…" : "Start subscription"}
          </Button>
        )}

        {subscription && subscription.status !== "none" && (
          <Button variant="secondary" onClick={handlePortal} disabled={redirecting}>
            {redirecting ? "Redirecting…" : "Manage billing"}
          </Button>
        )}
      </main>
    </>
  );
}
