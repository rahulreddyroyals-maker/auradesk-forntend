import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { DevEnvironmentBanner } from "@/components/shared/dev-environment-banner";

export const metadata: Metadata = {
  title: "AuraDesk — Your 24/7 AI Employee for Med Spas",
  description:
    "AuraDesk answers calls, books appointments, and recovers missed leads for med spas, 24/7.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased flex flex-col h-screen overflow-hidden">
        <DevEnvironmentBanner />
        <div className="flex-1 overflow-y-auto">
          <AuthProvider>{children}</AuthProvider>
        </div>
      </body>
    </html>
  );
}
