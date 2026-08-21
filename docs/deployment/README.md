# AuraDesk Deployment Documentation

Read these in order:

1. [`DEPLOYMENT_ARCHITECTURE.md`](./DEPLOYMENT_ARCHITECTURE.md) — services, ports, dependencies, what talks to what.
2. [`ENVIRONMENT_VARIABLES.md`](./ENVIRONMENT_VARIABLES.md) — every variable, which platform it belongs on, which are secrets.
3. [`VERCEL_SETUP.md`](./VERCEL_SETUP.md) — frontend deployment steps.
4. [`RAILWAY_SETUP.md`](./RAILWAY_SETUP.md) — backend deployment steps.
5. [`DNS_SETUP.md`](./DNS_SETUP.md) — domain/DNS records required.
6. [`PRODUCTION_CHECKLIST.md`](./PRODUCTION_CHECKLIST.md) — verify before calling it live.
7. [`ROLLBACK_PLAN.md`](./ROLLBACK_PLAN.md) — what to do if a deploy breaks something.
8. [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md) — common deployment issues and fixes.

## What this covers, honestly

This documents and prepares the codebase for deployment — Dockerfile,
Railway/Vercel config files, production start commands, security
headers, retry/failure handling, webhook idempotency. **It does not
include an actual live deployment** — I don't have access to create
Railway or Vercel accounts/projects on your behalf. Every config file
here has been validated locally (production build succeeds, backend
assembles and its test suite passes), but the real test is you running
through `RAILWAY_SETUP.md` and `VERCEL_SETUP.md` yourself.

Google Calendar integration, referenced in the original architecture
document as a target integration, **does not exist in this codebase** —
only an enum placeholder value. Section 12 of the deployment task
(Google Calendar OAuth) is therefore not applicable; documented as such
rather than fabricated. Sentry has code wired in (`app/main.py`) but no
DSN configured — see `ENVIRONMENT_VARIABLES.md`. PostHog has an unused
config placeholder and no integration code at all.
