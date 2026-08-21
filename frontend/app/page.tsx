import Link from "next/link";
import { Logo } from "@/components/shared/logo";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
        <Logo href="/" size={36} />
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/login" className="text-foreground/70 hover:text-foreground">
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-full bg-aura-ink-900 text-white px-4 py-2 text-sm font-medium hover:bg-aura-ink-700 transition-colors"
          >
            Get started
          </Link>
        </nav>
      </header>

      <main className="max-w-4xl mx-auto px-8 pt-20 pb-32 text-center">
        <p className="text-aura-gold-600 text-sm font-medium tracking-wide uppercase mb-4">
          Your 24/7 AI Employee for Med Spas
        </p>
        <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-[1.1]">
          Recover every missed lead.
          <br />
          Book more appointments.
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
          AuraDesk answers calls, texts, and DMs like a trained front desk employee —
          books appointments, answers pricing questions, and escalates when it matters.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/signup"
            className="rounded-full bg-aura-ink-900 text-white px-6 py-3 text-sm font-medium hover:bg-aura-ink-700 transition-colors"
          >
            Start free trial
          </Link>
          <Link
            href="#demo"
            className="rounded-full border border-border px-6 py-3 text-sm font-medium hover:bg-muted transition-colors"
          >
            Watch a demo call
          </Link>
        </div>
      </main>
    </div>
  );
}
