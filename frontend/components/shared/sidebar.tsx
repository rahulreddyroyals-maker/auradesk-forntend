"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navSections } from "@/lib/nav-config";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/shared/logo";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:shrink-0 h-full overflow-hidden border-r border-border bg-card/60 backdrop-blur-md">
      <div className="px-6 py-6">
        <Logo href="/dashboard" size={32} />
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-6 space-y-6">
        {navSections.map((section) => (
          <div key={section.title}>
            <p className="px-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-1.5">
              {section.title}
            </p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname?.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition-colors",
                      active
                        ? "bg-aura-gold-500/10 text-aura-gold-700 font-medium"
                        : "text-foreground/70 hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
