"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { Card } from "@/components/ui/primitives";
import { apiGet } from "@/lib/api-client";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from "recharts";

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

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Summary>("/analytics/summary")
      .then(setSummary)
      .catch(() => setError("Couldn't load analytics. Is the backend running?"));
  }, []);

  const channelData = summary
    ? [
        { name: "Calls", count: summary.calls_today },
        { name: "Texts", count: summary.texts_today },
        { name: "Chats", count: summary.chats_today },
      ]
    : [];

  return (
    <>
      <TopBar title="Analytics" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!summary && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {summary && (
          <>
            <Card>
              <p className="text-sm font-medium mb-4">Conversations by channel, today</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={channelData}>
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ fill: "rgba(201,162,75,0.08)" }} />
                    <Bar dataKey="count" fill="#C9A24B" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <div className="grid grid-cols-3 gap-4">
              <Card>
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Conversion Rate (7d)</p>
                <p className="text-2xl font-semibold">{(summary.conversion_rate_7d * 100).toFixed(0)}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Across {summary.total_conversations_7d} conversations
                </p>
              </Card>
              <Card>
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Avg Response Time</p>
                <p className="text-2xl font-semibold">
                  {summary.avg_response_seconds !== null ? `${summary.avg_response_seconds.toFixed(1)}s` : "—"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">Patient message to AI reply, today</p>
              </Card>
              <Card>
                <p className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Revenue Today</p>
                <p className="text-2xl font-semibold">${(summary.revenue_today_cents / 100).toFixed(0)}</p>
                <p className="text-xs text-muted-foreground mt-1">From AI-booked appointments</p>
              </Card>
            </div>
          </>
        )}
      </main>
    </>
  );
}
