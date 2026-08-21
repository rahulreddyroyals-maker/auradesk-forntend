# Deployment Architecture

## Target topology

```
                INTERNET
                   │
                   ▼
               VERCEL
                   │
            AuraDesk Web App
            Next.js 14 / React
                   │
                   ▼ (HTTPS + WSS)
               RAILWAY
                   │
          FastAPI Production API
          (single service — see
           "Background jobs" below
           for why there's no
           separate worker service)
                   │
      ┌────────────┼─────────────┬──────────────┬─────────────┐
      ▼            ▼              ▼              ▼             ▼
  Supabase       Groq          Twilio        Cartesia/      Meta
  PostgreSQL    LLM+STT       Voice/SMS     ElevenLabs   Messenger/IG
                                              (TTS)
```

No Google Calendar box in this diagram — it doesn't exist in the
codebase (see `README.md` in this directory). No Redis/queue box —
nothing in the codebase currently requires one (see below).

## Services

| Service | Framework | Deploys to | Notes |
|---|---|---|---|
| Frontend | Next.js 14 (App Router) | Vercel | Static + server-rendered pages, no custom server needed |
| Backend | FastAPI (Python 3.12) | Railway | One process serves REST API + one WebSocket endpoint (voice media streaming) |
| Database | Postgres | Supabase (existing — not migrating) | Two connection roles as of the RLS-hardening pass — see `ACCESS_CONTROL.md` in `/docs/security/` |

## Background jobs — why there's no separate worker service

The task's target architecture includes an optional worker service "if
background processing exists." It does, in a narrow sense:
`app/workers/followup_scheduler.py` re-engages leads who went quiet.
It's a standalone script (`python -m app.workers.followup_scheduler`),
not a long-running process — no message queue, no Celery, nothing that
needs its own always-on service. **Recommendation: run it as a Railway
Cron Job** (Railway supports scheduled jobs natively, pointed at the
same repo/image, running that one command on a schedule) rather than
standing up a second permanently-running service for something that
finishes in seconds. This avoids the "unnecessary infrastructure"
outcome the task explicitly warns against.

## Ports

- Backend: Railway injects `$PORT` at runtime (do not hardcode 8081 —
  that was only for local dev). The app binds `0.0.0.0:$PORT` via the
  `Procfile`/`Dockerfile` CMD.
- Frontend: Vercel manages this entirely; no port configuration needed.

## Dependencies requiring outbound network access from Railway

`api.groq.com`, `api.cartesia.ai`, `api.elevenlabs.io`,
`graph.facebook.com`, Twilio's API endpoints, and the Supabase Postgres
connection. Railway allows outbound traffic by default — nothing to
configure here, just confirming none of these are blocked by an
unexpected firewall rule.

## Webhooks (all require a public HTTPS URL — this is the actual reason
production deployment matters, vs. local dev)

| Webhook | Path | Vendor sets this to |
|---|---|---|
| SMS | `POST /api/v1/sms/webhook` | Twilio phone number's Messaging config |
| Voice | `POST /api/v1/calls/incoming` | Twilio phone number's Voice config |
| Voice media stream | `WSS /api/v1/calls/media-stream` | Referenced automatically by the TwiML the `/calls/incoming` handler returns — not configured directly in Twilio's dashboard |
| Messenger | `POST /api/v1/messenger/webhook` | Meta App Dashboard → Webhooks |
| Instagram | `POST /api/v1/instagram/webhook` | Meta App Dashboard → Webhooks |
| Stripe | `POST /api/v1/billing/webhook` | Stripe Dashboard → Webhooks |

All six require `api.<yourdomain>` (or whatever the Railway backend's
public URL is) to be reachable over HTTPS before they can be configured
— see `DNS_SETUP.md`.

## WebSocket support on Railway

Railway supports WebSockets over its standard HTTP routing — no special
configuration needed for `/api/v1/calls/media-stream` beyond the app
listening on `$PORT` like everything else. Confirm this once deployed
(see `PRODUCTION_CHECKLIST.md`) since this hasn't been tested against a
live Railway deployment in this pass.

## Health check

`GET /health` → `{"status": "ok", "environment": "production"}` — no
database query, no external calls, so it reflects "the process is
running" rather than "every dependency is reachable." This is
intentional: a health check that queries the database would make
Railway restart the service during a transient Supabase blip, which is
worse than just serving degraded responses briefly.
