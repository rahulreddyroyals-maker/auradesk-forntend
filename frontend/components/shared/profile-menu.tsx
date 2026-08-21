"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { LogOut, Settings, ChevronDown } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { createClient } from "@/lib/supabase/client";

export function ProfileMenu() {
  const { session } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handleLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  }

  const email = session?.user?.email ?? "";
  const initial = email ? email[0].toUpperCase() : "?";

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-full pl-1 pr-2 py-1 hover:bg-muted transition-colors"
        aria-label="Account menu"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-aura-ink-900 text-white text-xs font-medium dark:bg-aura-gold-500 dark:text-aura-ink-900">
          {initial}
        </div>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border bg-card shadow-glass py-1.5 z-50">
          {email && (
            <div className="px-3 py-2 border-b border-border">
              <p className="text-sm font-medium truncate">{email}</p>
            </div>
          )}
          <Link
            href="/settings"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
          >
            <Settings className="h-4 w-4 text-muted-foreground" />
            Settings
          </Link>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
