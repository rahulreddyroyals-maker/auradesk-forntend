import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { History } from "lucide-react";

export default function ConversationHistoryPage() {
  return (
    <>
      <TopBar title="Conversation History" />
      <main className="flex flex-1 flex-col p-8">
        <EmptyState
          icon={History}
          title="No data yet"
          description="A searchable archive of every past conversation across all channels."
        />
      </main>
    </>
  );
}
