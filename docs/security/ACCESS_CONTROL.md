# Access Control

## Authentication

- Supabase Auth, email/password. JWTs verified server-side against
  either ES256 (JWKS, current Supabase default) or HS256 (legacy secret)
  — see `app/core/security.py`.
- Session expiration: whatever Supabase's default JWT lifetime is
  (typically ~1 hour access token, refreshed via a longer-lived refresh
  token) — not overridden by this codebase.
- **MFA: NOT IMPLEMENTED.** Supabase Auth supports TOTP-based MFA
  natively; this codebase doesn't yet expose an enrollment/challenge
  flow for it. Flagged as a required enhancement before handling real
  PHI — HIPAA's Security Rule strongly favors it for anyone with access
  to ePHI, even though HIPAA doesn't literally mandate MFA by name.
- **Rate limiting / brute-force protection on login: relies entirely on
  Supabase Auth's own built-in protections.** Not independently verified
  or supplemented by this codebase.
- Password reset: handled entirely by Supabase Auth's own flow, not
  custom code in this repo.

## Authorization (RBAC)

Three roles exist today: `owner`, `admin`, `front_desk` (see
`app/models/tenancy.py::StaffRole`). The task's suggested role set
(OWNER / ADMIN / MANAGER / STAFF / AI_AGENT / SUPER_ADMIN) is broader
than what's implemented — current `require_role()` checks
(`app/api/deps.py`) gate team management and billing to
`owner`/`admin` only; most other endpoints only require *any*
authenticated staff member of the clinic, not a specific role. A
finer-grained RBAC pass (e.g., restricting who can view raw
conversation content vs. just appointment scheduling) is a real gap —
flagged as PARTIALLY IMPLEMENTED.

There is no `AI_AGENT` or `SUPER_ADMIN` role — the AI never
authenticates as a "user" (it runs entirely inside backend-controlled
code paths, see `AI_SAFETY.md` for why the LLM never makes its own
authorization decisions), and there's no cross-tenant super-admin role
in the application layer (Supabase's own dashboard is the only
cross-tenant access point, and that's Supabase-account-level, not this
app's).

## Tenant isolation (the most safety-critical property in a multi-tenant
medical app)

Two layers, deliberately:

1. **Application-level**: every database query across all 44 endpoints
   was audited this pass and confirmed to filter by `clinic_id`
   correctly. This was already true before this pass.
2. **Database-level (RLS)**: as of this pass, actually enforced, not
   just documented. The backend connects via two roles:
   - `auradesk_app` (restricted, not a table owner) — Postgres applies
     Row-Level Security to this role automatically. This is what every
     normal authenticated request uses.
   - An admin role (bypasses RLS) — used *only* for migrations and a
     small, explicitly-commented set of bootstrapping operations
     (onboarding's clinic-creation step, and each webhook's initial
     "which clinic does this belong to" lookup) that structurally can't
     be RLS-scoped, since no `clinic_id` claim can exist before that
     lookup resolves it.

   See `sql/restrict_app_role.sql` and `app/db/session.py` for the full
   implementation. This is opt-in (falls back to the old single-role
   behavior if `DATABASE_URL_ADMIN` isn't set) — **must be turned on
   before production use.**

3. A subtler bug was found and fixed in this same pass: Postgres's RLS
   claim-setting mechanism is scoped to the current transaction, and
   several request handlers commit partway through and query again —
   which would have silently lost the claim mid-request. Fixed via
   `bind_clinic_context()`'s session-event-based re-application,
   verified with a test proving the claim survives a mid-session commit.

## Automated cross-tenant testing

See `SECURITY_TESTING.md` and `/backend/tests/security/` — a
cross-tenant IDOR test exists as of this pass, exercising the actual
query-scoping logic.
