"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8081/api/v1";

export function DevEnvironmentBanner() {
  const [environment, setEnvironment] = useState<string | null>(null);

  useEffect(() => {
    // Source of truth is the backend's own ENVIRONMENT setting, not a
    // frontend-only guess — so this banner reflects what the backend
    // actually believes it is, not what NODE_ENV happens to say.
    fetch(`${API_BASE.replace(/\/api\/v1$/, "")}/health`)
      .then((r) => r.json())
      .then((data) => setEnvironment(data.environment))
      .catch(() => {
        // Backend unreachable — fail safe by assuming non-production,
        // since we'd rather over-warn than silently show nothing.
        setEnvironment("unknown");
      });
  }, []);

  if (environment === "production") return null;
  if (environment === null) return null; // don't flash the banner while checking

  return (
    <div className="flex items-center justify-center gap-2 bg-amber-500 px-4 py-1.5 text-xs font-medium text-amber-950">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      DEVELOPMENT ENVIRONMENT — DO NOT ENTER REAL PATIENT INFORMATION
    </div>
  );
}
