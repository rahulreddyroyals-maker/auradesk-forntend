"use client";

import { useEffect, useState } from "react";
import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { Card } from "@/components/ui/primitives";
import { apiGet, apiPatch } from "@/lib/api-client";
import { CalendarCheck } from "lucide-react";

interface AppointmentItem {
  id: string;
  patient_name: string;
  service_name: string;
  start_time: string;
  end_time: string;
  status: string;
  booked_by: string;
}

const statusStyles: Record<string, string> = {
  booked: "bg-blue-500/10 text-blue-700",
  confirmed: "bg-green-500/10 text-green-700",
  rescheduled: "bg-amber-500/10 text-amber-700",
  canceled: "bg-red-500/10 text-red-700",
  completed: "bg-muted text-muted-foreground",
  no_show: "bg-red-500/10 text-red-700",
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setAppointments(await apiGet<AppointmentItem[]>("/appointments"));
    } catch {
      setError("Couldn't load appointments. Is the backend running?");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleStatusChange(id: string, status: string) {
    try {
      await apiPatch(`/appointments/${id}`, { status });
      await load();
    } catch {
      setError("Couldn't update that appointment.");
    }
  }

  return (
    <>
      <TopBar title="Appointments" />
      <main className="flex flex-1 flex-col p-8 gap-6">
        <p className="text-sm text-muted-foreground max-w-lg">
          Appointments booked by your AI Employee (and any you add manually) — this is where all
          that booking activity actually shows up.
        </p>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {appointments === null && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

        {appointments !== null && appointments.length === 0 && (
          <EmptyState
            icon={CalendarCheck}
            title="No appointments yet"
            description="Once your AI Employee books someone — or you add one manually — it'll show up here."
          />
        )}

        {appointments !== null && appointments.length > 0 && (
          <Card className="p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Patient</th>
                  <th className="px-4 py-3 font-medium">Service</th>
                  <th className="px-4 py-3 font-medium">When</th>
                  <th className="px-4 py-3 font-medium">Booked by</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((a) => (
                  <tr key={a.id} className="border-b border-border last:border-0">
                    <td className="px-4 py-3 font-medium">{a.patient_name}</td>
                    <td className="px-4 py-3">{a.service_name}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatTime(a.start_time)}</td>
                    <td className="px-4 py-3 text-muted-foreground capitalize">{a.booked_by}</td>
                    <td className="px-4 py-3">
                      <select
                        value={a.status}
                        onChange={(e) => handleStatusChange(a.id, e.target.value)}
                        className={`rounded-full border-0 px-2.5 py-0.5 text-[11px] font-medium capitalize outline-none ${statusStyles[a.status] ?? "bg-muted"}`}
                      >
                        {["booked", "confirmed", "rescheduled", "canceled", "completed", "no_show"].map((s) => (
                          <option key={s} value={s}>
                            {s.replace("_", " ")}
                          </option>
                        ))}
                      </select>
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
