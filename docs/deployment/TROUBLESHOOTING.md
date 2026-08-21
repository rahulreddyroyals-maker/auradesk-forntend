# Troubleshooting

Written from the actual issues hit repeatedly during this project's
local development — the production equivalents of the same root causes.

## "Failed to fetch" on the frontend

Almost always means the browser couldn't reach the backend at all —
not an HTTP error, a network-level failure. In production, check:
1. Is `NEXT_PUBLIC_API_BASE_URL` set correctly for this environment
   (and did you redeploy after changing it — env var changes need a
   redeploy on Vercel)?
2. Is the Railway service actually running (check Railway's deploy
   logs/status)?
3. Is `FRONTEND_ORIGINS` on the backend missing this exact frontend
   origin? A CORS block often surfaces to the browser as the same
   generic "Failed to fetch" rather than an obvious CORS error message.

## 401/403 errors after a fresh deploy

If you rotated `SUPABASE_JWT_SECRET` or changed
`SUPABASE_URL`/`SUPABASE_ANON_KEY` without users re-authenticating,
existing sessions will fail verification. Users need to log out and
back in to get a token signed against the current configuration.

## Onboarding or any clinic-scoped request returns empty/403 after
switching to the restricted DB role

Means the RLS claim isn't being set for that code path — see
`/docs/security/ACCESS_CONTROL.md` for the two-role architecture. Check
that `DATABASE_URL_ADMIN` is actually set (not falling back to the
restricted `DATABASE_URL`) for operations that need it, and that
`bind_clinic_context()` is called before any clinic-scoped query.

## Migration fails with "invalid interpolation syntax" or similar

If your database password contains `%`, `@`, or other special
characters, make sure it's URL-encoded in the connection string (`@` →
`%40`, etc.) — see the migration `env.py`'s handling of this; it
deliberately avoids Alembic's `ConfigParser`-based URL storage for
exactly this reason, but a malformed URL string itself will still fail
regardless.

## Twilio webhook returns errors / calls don't connect

1. Confirm `TWILIO_VALIDATE_SIGNATURE=true` in production, and that the
   webhook URL configured in Twilio's dashboard exactly matches what
   the app receives as its own public URL (mismatches here cause valid
   requests to fail signature validation).
2. Confirm the clinic's `phone_number` in the database matches
   `TWILIO_PHONE_NUMBER` exactly, including the `+1` country code
   prefix.

## Voice calls connect but no audio / call drops immediately

Check that the WebSocket endpoint (`wss://api.auradesk.com/api/v1/calls/media-stream`)
is actually reachable — this specific path (WebSocket through Railway's
routing, behind a custom domain) was not tested against live
infrastructure in this pass. If it fails, temporarily test against
Railway's default `*.up.railway.app` URL to isolate whether the issue
is the custom domain/proxy or the WebSocket handling itself.

## Groq/Cartesia/ElevenLabs errors in logs

Check `app/integrations/groq_client.py`'s retry logic — transient
failures (timeouts, 5xx, 429) retry automatically with backoff; if you
see `groq_unavailable_fallback` in the structured logs, it means
retries were exhausted and the conversation was escalated to a human
rather than left broken. That's the intended failure-safe behavior, not
a bug — but repeated occurrences point to a real Groq outage or an
exhausted rate limit worth investigating on Groq's side.

## Rate limiting blocks legitimate webhook traffic

`app/core/rate_limit.py`'s `MAX_REQUESTS_PER_WINDOW = 30` per IP per
minute is a starting guess, not a measured production value. If a
legitimate high-traffic clinic (or Twilio's own retry behavior under
load) trips it, raise the limit — and remember this is in-memory,
single-process only; if you ever run more than one Railway instance,
each tracks its own count, so the effective limit multiplies by
instance count (documented in that file's own comments).
