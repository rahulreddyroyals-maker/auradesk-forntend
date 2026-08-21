import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { CalendarDays } from "lucide-react";

export default function CalendarPage() {
  return (
    <>
      <TopBar title="Calendar" />
      <main className="flex flex-1 flex-col p-8">
        <EmptyState
          icon={CalendarDays}
          title="No data yet"
          description="A calendar view of upcoming appointments across your providers."
        />
      </main>
    </>
  );
}
