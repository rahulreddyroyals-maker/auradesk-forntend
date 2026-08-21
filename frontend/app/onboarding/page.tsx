"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { apiPost } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input, Label, Card } from "@/components/ui/primitives";

export default function OnboardingPage() {
  const router = useRouter();
  const [clinicName, setClinicName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiPost("/onboarding/clinic", {
        clinic_name: clinicName,
        owner_name: ownerName,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York",
      });

      // The JWT the browser is currently holding has no clinic_id claim —
      // it was issued before the Staff row existed. Refreshing the session
      // forces Supabase to re-run the Auth Hook and mint a token that has it.
      const supabase = createClient();
      const { error: refreshError } = await supabase.auth.refreshSession();
      if (refreshError) throw refreshError;

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <h1 className="text-lg font-medium mb-1">Set up your clinic</h1>
        <p className="text-sm text-muted-foreground mb-6">
          This creates your clinic workspace and your AI Employee.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="clinicName">Clinic name</Label>
            <Input
              id="clinicName"
              required
              value={clinicName}
              onChange={(e) => setClinicName(e.target.value)}
              placeholder="Radiance Med Spa"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ownerName">Your name</Label>
            <Input
              id="ownerName"
              required
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
              placeholder="Jamie Rivera"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Setting up…" : "Create clinic"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
