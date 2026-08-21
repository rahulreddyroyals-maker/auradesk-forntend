"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none",
          variant === "primary" && "bg-aura-ink-900 text-white hover:bg-aura-ink-700 dark:bg-aura-gold-500 dark:text-aura-ink-900 dark:hover:bg-aura-gold-300",
          variant === "secondary" && "border border-border bg-card hover:bg-muted",
          variant === "ghost" && "hover:bg-muted",
          variant === "danger" && "text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
