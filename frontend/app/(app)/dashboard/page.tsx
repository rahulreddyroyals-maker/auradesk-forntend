"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { Card } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { Phone, MessageSquare, MessagesSquare, CalendarCheck, UserX, DollarSign, TrendingUp, Timer } from "lucide-react";

interface Summary {
  calls_today: number;
  texts_today: number;
  chats_today: number;
  booked_today: number;
  missed_leads_today: number;
  revenue_today_cents: number;
  upcoming_appointments: number;
  conversion_rate_7d: number;
  avg_response_seconds: number | null;
  total_conversations_7d: number;
}

function StatCard({ icon: Icon, label, value, sub }: { icon: typeof Phone; label: string; value: string; sub?: string }) {
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-semibold">{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </Card>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Summary>("/analytics/summary")
      .then(setSummary)
      .catch(() => setError("Couldn't load your dashboard. Is the backend running?"));
  }, []);

  return (
    <>
      <TopBar title="Dashboard" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!summary && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {summary && (
          <div className="grid grid-cols-4 gap-4">
            <StatCard icon={Phone} label="Calls Today" value={String(summary.calls_today)} />
            <StatCard icon={MessageSquare} label="Texts Today" value={String(summary.texts_today)} />
            <StatCard icon={MessagesSquare} label="Chats Today" value={String(summary.chats_today)} />
            <StatCard icon={CalendarCheck} label="Booked Today" value={String(summary.booked_today)} />
            <StatCard icon={UserX} label="Missed Leads Today" value={String(summary.missed_leads_today)} />
            <StatCard
              icon={DollarSign}
              label="Revenue Today"
              value={`$${(summary.revenue_today_cents / 100).toFixed(0)}`}
            />
            <StatCard icon={CalendarCheck} label="Upcoming Appointments" value={String(summary.upcoming_appointments)} />
            <StatCard
              icon={TrendingUp}
              label="Conversion Rate (7d)"
              value={`${(summary.conversion_rate_7d * 100).toFixed(0)}%`}
              sub={`${summary.total_conversations_7d} conversations`}
            />
            <StatCard
              icon={Timer}
              label="Avg Response Time"
              value={summary.avg_response_seconds !== null ? `${summary.avg_response_seconds.toFixed(1)}s` : "—"}
            />
          </div>
        )}
      </main>
    </>
  );
}
