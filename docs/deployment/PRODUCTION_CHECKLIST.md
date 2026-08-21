# Production Checklist

Every item here requires a live deployment to actually verify — I could
validate the code locally (build success, unit/integration tests) but
not these end-to-end behaviors against real Vercel/Railway/Supabase
infrastructure. Work through this in order after deploying.

## Basic functionality
- [ ] Frontend loads at the production domain
- [ ] Signup works (creates a Supabase Auth user)
- [ ] Login works
- [ ] Logout works (confirm the session is actually cleared, not just
      redirected)
- [ ] Onboarding creates a clinic + staff + AI employee row
- [ ] Dashboard loads and shows real (zeroed, for a fresh clinic) data
- [ ] Every CRUD page works: Knowledge Base, Services, Patients,
      Appointments, Team, Integrations, Settings

## Data & tenancy
- [ ] Database reads work
- [ ] Database writes work
- [ ] **Tenant isolation**: create two clinics, confirm clinic A cannot
      see clinic B's patients/conversations/appointments through any
      page — this is the single most important check in this entire
      list for a multi-tenant medical-adjacent app
- [ ] If you've switched to the restricted `auradesk_app` role (see
      `/docs/security/`), confirm normal CRUD still works — this is
      where a missed `bind_clinic_context()` call would surface as
      silently empty results

## AI Employee
- [ ] AI Employee test console gets a real reply from Groq
- [ ] Knowledge base lookup returns grounded answers, not hallucinated
      ones
- [ ] Appointment booking actually creates an `appointments` row
- [ ] Human escalation actually creates an `escalations` row and texts
      staff

## Channels (each requires the vendor's dashboard pointed at the real
production URL — none of these can be tested against localhost)
- [ ] Twilio inbound SMS reaches the webhook and gets a reply
- [ ] Twilio inbound call connects, and voice actually flows both ways
- [ ] Messenger message reaches the webhook and gets a reply
- [ ] Instagram message reaches the webhook and gets a reply
- [ ] Stripe checkout completes and the webhook updates subscription
      status

## Security
- [ ] Webhook signature validation actually rejects a forged request
      (try sending a POST to `/sms/webhook` without a valid Twilio
      signature — `TWILIO_VALIDATE_SIGNATURE=true` must be set)
- [ ] A user with no session gets 401 on protected endpoints
- [ ] A `front_desk`-role user cannot access Team/Billing management
- [ ] No secret appears in browser DevTools (Network tab, page source,
      or `NEXT_PUBLIC_*` env inspection)
- [ ] No secret appears in the Git repository (run a secret scanner if
      you have one available, or manually grep the diff before merging
      any change touching config)
- [ ] No secret or patient content appears in Railway's logs — spot
      check a few real log lines against `/docs/security/AI_SAFETY.md`'s
      redaction rules
- [ ] HTTPS is enforced (Vercel and Railway both do this by default —
      confirm no `http://` fallback is reachable)
- [ ] CORS only allows the actual production frontend origin, not `*`

## Observability
- [ ] Production logs are visible and readable in Railway
- [ ] Vercel logs are visible for frontend errors
- [ ] Sentry: **only check this if you've actually set `SENTRY_DSN`** —
      the integration code exists but has never been verified against
      a live Sentry project in this codebase's history

## Failure handling — see `TROUBLESHOOTING.md` for the reasoning behind
each of these; the point of this section is confirming the fail-safe
behavior in `AI_SAFETY.md`/the orchestrator actually holds under real
failure conditions, not just in the mocked tests from this pass
- [ ] Temporarily use an invalid `GROQ_API_KEY` and confirm the AI
      Employee escalates gracefully instead of the request hanging or
      erroring visibly to the patient
- [ ] Send a webhook with an invalid signature and confirm it's
      rejected with a clean error, not a 500
- [ ] Send the same Twilio SMS webhook payload twice (simulating a
      retry) and confirm only one reply is sent
- [ ] Request a nonexistent appointment ID and confirm a clean 404, not
      a 500 or a stack trace leaking to the client
- [ ] Trigger the rate limiter (send 30+ rapid requests to a webhook
      endpoint) and confirm it returns 429 cleanly

## Domain & infra
- [ ] Production domain resolves and serves the app
- [ ] `app.auradesk.com` → Vercel, `api.auradesk.com` → Railway, per
      `DNS_SETUP.md`
- [ ] Health check endpoint (`/health`) is reachable and Railway shows
      the service as healthy
