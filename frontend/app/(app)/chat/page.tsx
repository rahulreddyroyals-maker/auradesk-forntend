import { TopBar } from "@/components/shared/top-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { MessagesSquare } from "lucide-react";

export default function WebsiteChatPage() {
  return (
    <>
      <TopBar title="Website Chat" />
      <main className="flex flex-1 flex-col p-8">
        <EmptyState
          icon={MessagesSquare}
          title="No data yet"
          description="Live and past website chat sessions will appear here."
        />
      </main>
    </>
  );
}
