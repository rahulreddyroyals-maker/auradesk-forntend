# AuraDesk — Production Deployment Prep (Vercel + Railway)

Your 24/7 AI Employee for Med Spas.

This pass prepared the existing application for deployment — no
architecture changes, no rebuild. See `/docs/deployment/README.md` for
the complete guide. Real engineering hardening included this pass:
production start commands, security headers, Groq retry/failure
handling (with graceful escalation if the AI service is down), webhook
idempotency, and Docker/Railway/Vercel configuration — all validated
locally (backend assembles, 22 security tests pass, frontend builds
clean across all 27 routes).

**This does not include an actual live deployment** — creating the
Railway/Vercel projects, DNS, and going live requires your own
accounts. Full checklist for that in `/docs/deployment/PRODUCTION_CHECKLIST.md`.

This pass also completed the previous HIPAA-readiness and RLS-hardening
work. See `/docs/security/` for that, then the phase history below.

## Run and deploy instructions (local dev — unchanged by this pass)

```powershell
cd backend
pip install -r requirements.txt
python -m alembic upgrade head    # includes audit_logs from the HIPAA pass
python -m pytest tests/security/ -v   # confirm all 22 security tests pass
```

Frontend: no new local-dev-relevant dependencies this pass — restart
the dev server to pick up the security headers config
(`next.config.js`) and `vercel.json`. New files this pass
(`Dockerfile`, `railway.json`, `Procfile`) only matter once you're
actually deploying — see `/docs/deployment/`.

## Audit findings

**Application-level tenant scoping: clean.** Every write, update, and
delete across all 44 endpoints filters by `clinic_id` correctly. Webhook
entry points (SMS, Voice, Messenger, Instagram, Stripe) correctly
resolve the clinic from an external identifier (phone number, page ID,
Stripe customer ID) rather than trusting client input — the right
pattern for endpoints Twilio/Meta/Stripe call directly.

**RLS was documentation, not enforcement — now fixed.** Since Phase 0,
the backend has connected as the `postgres` table-owner role, which
Postgres automatically exempts from its own RLS policies. That meant
every correct `clinic_id` filter in application code was the *only*
thing preventing cross-tenant access — RLS added no actual protection.
Fine for development; not what you want with 50 real businesses' patient
data in one database. This is now fixed with a genuine two-role
architecture:

- **`DATABASE_URL`** (new, opt-in): connects as a restricted
  `auradesk_app` role (`sql/restrict_app_role.sql`) that is *not* a
  table owner — Postgres actually applies RLS to it. This is what every
  normal authenticated request uses now.
- **`DATABASE_URL_ADMIN`**: your existing `postgres` connection.
  Bypasses RLS. Used *only* where that's structurally necessary —
  migrations (DDL — the restricted role deliberately has no CREATE/DROP
  rights), onboarding's clinic-creation step (there's no `clinic_id`
  claim to check yet — that's the row being created), and each
  webhook's initial "which clinic does this belong to" lookup (same
  reasoning — you can't RLS-scope a query whose whole job is to
  *discover* the clinic_id). Every one of these is a single, narrow,
  clearly-commented query — not a blanket bypass.

This is **opt-in and backward-compatible** — `DATABASE_URL_ADMIN` falls
back to `DATABASE_URL` automatically, so nothing breaks if you don't set
it up yet. Recommended before real client data flows through.

I also found and fixed a subtler bug while building this: Postgres's
`set_config(..., true)` (which sets the RLS claim) is scoped to the
*current transaction* — and several webhook handlers commit partway
through a request and then query again afterward. Under the restricted
role, that second query would have silently lost its claim and returned
nothing, with no error — a "data mysteriously vanishes after saving"
bug that would only surface once RLS was actually enforced. Fixed with
`bind_clinic_context()` (`app/db/session.py`), which uses a SQLAlchemy
session event to re-apply the claim at the start of *every* transaction
on a session, not just once — verified with a test that proves the
claim survives a mid-session commit.

## Setting up the restricted role

1. Run `sql/restrict_app_role.sql` in the Supabase SQL editor — **edit
   the placeholder password first**, this is a real credential.
2. Grab the connection string the same way you did for `DATABASE_URL`
   originally, but with `auradesk_app` as the username and the password
   you set.
3. Set that as `DATABASE_URL`. Set your *existing* `postgres` connection
   string as `DATABASE_URL_ADMIN`.
4. Restart the backend. Try onboarding a fresh clinic and using a few
   CRUD pages — this exercises both the restricted role (normal
   requests) and the admin role (onboarding) in one pass.

## What I did NOT get to in this pass (recommended next)

Being upfront about the rest of the punch list, in priority order:

- **N+1 query patterns**: `conversations.py`, `appointments.py`,
  `escalations.py`, and `logs.py` each fetch related rows (patient,
  service) one-by-one in a loop rather than via a join or batch query.
  Fine at today's data volumes; worth fixing before 50 clinics' worth of
  conversation history makes those list endpoints noticeably slow.
- **Rate limiting on public webhook endpoints**: nothing currently
  stops a bad actor from hammering `/sms/webhook` or
  `/messenger/webhook` to run up your Groq/Twilio/Cartesia bill — the
  signature checks confirm the *sender* is legitimate, but not the
  *volume*. Worth a basic per-clinic or per-IP rate limiter.
- **JWT revocation lag**: removing a team member (Team page) deletes
  their `staff` row, but their *existing* access token stays valid
  until it naturally expires (Supabase's default session lifetime) —
  it's not immediately revoked. Standard tradeoff of stateless JWTs, not
  unique to this app, but worth knowing rather than assuming removal is
  instant.
- **Connection pool sizing**: current pool (`pool_size=10,
  max_overflow=20` per engine, and now *two* engines) should be
  comfortable for 50 clinics on Supabase's pooler, but hasn't been
  load-tested — worth revisiting if you see connection exhaustion
  errors under real traffic.

## What's real in this build

- **Dashboard & Analytics**: all the metrics from the original spec —
  calls/texts/chats today, booked today, missed leads, revenue
  generated, upcoming appointments, 7-day conversion rate, average
  response time — computed from real conversation/appointment/message
  data, not placeholders. I tested all six non-trivial calculations
  against known synthetic data before trusting them (see the test output
  from this session if you want the receipts).
- **Appointments page**: finally a place to see what your AI Employee
  has booked, with inline status updates (confirm, cancel, mark
  completed/no-show).
- **Team management**: real invites via Supabase's admin API (sends an
  actual invite email with a magic link), role management, and removal
  — with a safety check preventing you from removing the last owner.
- **Logs page**: every tool call your AI Employee has made — knowledge
  base lookups, bookings, escalations — flattened from the audit trail
  that's been recording since Phase 2.
- **Billing** (`app/integrations/stripe_client.py`,
  `/api/v1/billing/*`): checkout, customer portal, and webhook handling
  for subscription status. Untested against a live Stripe account — same
  status as Twilio/Meta until you've configured real keys.
- Everything from Phase 0–5.

This completes the original 6-phase roadmap. Known simplifications that
remain (all called out in earlier phase notes, still true): keyword-based
KB search instead of pgvector similarity, per-turn batch voice STT/TTS
instead of continuous streaming, and RLS as defense-in-depth rather than
the primary tenant-isolation layer (the backend connects as table owner,
which Postgres exempts from RLS by default — application-level
`clinic_id` filtering on every query is the real enforcement).

## Billing setup (Stripe)

1. Create a Stripe account, get your test-mode secret key.
2. Create a recurring monthly **Price** in the Stripe dashboard, and set
   its **lookup key** to `auradesk_monthly` (or change
   `MONTHLY_PRICE_LOOKUP_KEY` in `app/integrations/stripe_client.py` to
   match whatever you use).
3. Set `STRIPE_SECRET_KEY` in `backend/.env`.
4. **Run the new migration**: `python -m alembic upgrade head` — adds
   the `subscriptions` table.
5. For the webhook (subscription status updates): install the Stripe
   CLI, run `stripe listen --forward-to localhost:8081/api/v1/billing/webhook`,
   and copy the signing secret it prints into `STRIPE_WEBHOOK_SECRET`.
6. Try "Start subscription" from the Billing page.

## Messenger / Instagram setup (Meta + ngrok)

1. Create a Meta Developer account and app at developers.facebook.com,
   adding both the Messenger and Instagram Messaging products.
2. Connect your Facebook Page (and its linked Instagram Business
   account) to the app, and generate a Page Access Token.
3. Set `META_APP_SECRET` (from your app's Basic Settings) and
   `META_VERIFY_TOKEN` (any string you choose — you'll enter this same
   value in Meta's dashboard) in `backend/.env`.
4. In the app, go to Integrations and connect Messenger and/or
   Instagram — paste your Page ID and Page Access Token there.
5. Run `ngrok http 8081` if it isn't already running (same tunnel as
   SMS/Voice).
6. In the Meta App Dashboard's Webhooks settings, subscribe your Page to
   the `messages` field, set the callback URL to
   `https://<your-ngrok-url>/api/v1/messenger/webhook`, and the verify
   token to whatever you set as `META_VERIFY_TOKEN`. Repeat for
   Instagram with `.../instagram/webhook` if using a separate
   subscription.
7. Message your Page (or its Instagram account) from a personal account.

## SMS setup (Twilio + ngrok)

1. **Create a Twilio account** at twilio.com (free trial works for
   testing) and buy a phone number with SMS capability (Console → Phone
   Numbers → Buy a number).
2. **Copy your credentials** from the Twilio Console dashboard into
   `backend/.env`: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and
   `TWILIO_PHONE_NUMBER` (the number you just bought, in `+1XXXXXXXXXX`
   format).
3. **Set the same number on your clinic** via the Settings page in the
   app — must match `TWILIO_PHONE_NUMBER` exactly.
4. **Install and run ngrok** (https://ngrok.com — free tier is fine):
   ```powershell
   ngrok http 8081
   ```
   This prints a public URL like `https://abcd1234.ngrok-free.app` that
   tunnels to your local backend. Keep this terminal running alongside
   your backend and frontend terminals.
5. **Point Twilio at your tunnel**: in the Twilio Console, open your
   phone number's settings, find "A MESSAGE COMES IN", set it to
   Webhook, and enter `https://<your-ngrok-url>/api/v1/sms/webhook`
   (POST). Save.
6. **Text your Twilio number** from your phone.

Every time you restart ngrok, the URL changes (on the free tier) — update
the Twilio webhook URL(s) again if so, for both SMS and Voice.

## Voice setup (Twilio Voice + ngrok)

Same ngrok tunnel as SMS handles this too — one tunnel, two Twilio
webhook configurations pointing at the same backend:

1. Same Twilio number works for both SMS and Voice — no need to buy a
   second one, just enable Voice capability if you haven't.
2. Set `CARTESIA_API_KEY` and `ELEVENLABS_API_KEY` in `backend/.env`.
3. In the Twilio Console, open your number's settings, find "A CALL
   COMES IN", set it to Webhook, and enter
   `https://<your-ngrok-url>/api/v1/calls/incoming` (POST). Save.
4. Call your Twilio number from your phone.

If it doesn't behave naturally at first (cuts you off too early, or
waits too long after you stop talking), that's the silence-detection
thresholds needing a tune for your actual voice/environment — let me
know what you're seeing and we'll adjust the constants in
`voice_pipeline.py` together.

## Running the follow-up worker

Manually, to test:
```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m app.workers.followup_scheduler
```

To run it automatically every 30 minutes on Windows: open Task
Scheduler → Create Task → set the trigger to repeat every 30 minutes →
set the action to run `D:\auradesk\backend\.venv\Scripts\python.exe`
with argument `-m app.workers.followup_scheduler` and "Start in"
`D:\auradesk\backend`.

## Local setup

### Backend

macOS/Linux:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase + Twilio + Groq + Cartesia keys
alembic upgrade head
uvicorn app.main:app --reload
```

Windows (PowerShell):
```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8081
```
If `Activate.ps1` is blocked, run once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

> This project defaults to port **8081** for the backend and **3001** for
> the frontend (instead of the usual 8000/3000) to avoid clashing with
> other local projects. Adjust `FRONTEND_ORIGINS` in `.env` and
> `NEXT_PUBLIC_API_BASE_URL` in `.env.local` if you use different ports.

### Database (Supabase)
1. Create a Supabase project, grab the Postgres connection string for `DATABASE_URL`.
2. Run `alembic upgrade head` from `/backend` to create all tables.
3. Run `sql/rls_policies.sql` against the same database (Supabase SQL editor or `psql`).
4. In the Supabase dashboard → Authentication → Hooks, enable the
   "Custom Access Token" hook and point it at `public.custom_access_token_hook`
   (created by `rls_policies.sql`) so every session JWT carries `clinic_id`/`role`.

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in Supabase URL/anon key + API base URL
npm run dev -- -p 3001
```

## What's still not real

A few pages remain empty-state stubs — Calendar (a visual calendar view;
Appointments has the same data as a list), Chat and Conversation History
(Inbox already covers this — these were meant as more specialized views
that never got split out), Patients editing (create/list work, edit
doesn't yet).

And the known simplifications from earlier phases, unchanged:
keyword-based KB search instead of pgvector similarity, per-turn batch
voice STT/TTS instead of continuous streaming, and RLS as defense-in-depth
rather than the primary tenant-isolation layer.

Everything else in the original spec — all 14 MVP features, all the
dashboard metrics, all 19 pages functioning (not just navigable) — is
built and, where I had the tools to check, verified: unit tests, mocked
integration tests, real HTTP requests through FastAPI's test client, and
cryptographic signature verification, documented in each phase's notes
above. What I could *not* verify is anything requiring your actual
Twilio, Meta, Stripe, or Supabase production credentials — those are
real integrations, not mocks, but this session never had live access to
test them end-to-end. That's the honest state of things as you head into
production setup.
