import Link from "next/link";
import { Bell } from "lucide-react";
import { ProfileMenu } from "@/components/shared/profile-menu";

export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex items-center justify-between border-b border-border px-8 py-4 shrink-0">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <div className="flex items-center gap-2">
        <Link
          href="/notifications"
          aria-label="Notifications"
          className="rounded-full p-2 hover:bg-muted transition-colors"
        >
          <Bell className="h-5 w-5 text-muted-foreground" />
        </Link>
        <ProfileMenu />
      </div>
    </header>
  );
}
