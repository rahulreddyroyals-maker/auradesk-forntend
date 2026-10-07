# AuraDesk Demo — Setup & Narration Guide

A standing, fully-populated demo clinic ("Glow Aesthetic Studio") that you
can share with prospective med-spa clients as a real, working login — not
screenshots. This doc covers: deploying it, reseeding it before a call, and
narrating it confidently.

## 1. What got added

**Backend**
- `app/api/v1/demo.py` — new router with two endpoints:
  - `GET /api/v1/demo/info` — public, read-only. Returns the clinic name and
    login email/password for the frontend's `/demo` page to display.
  - `POST /api/v1/demo/reseed` — protected by a secret header. Wipes and
    regenerates the demo clinic's "activity" (patients, conversations,
    messages, calls, escalations, appointments, subscription), anchored to
    the current time, so the dashboard always looks like it happened in the
    last few days. The login, clinic, services, and knowledge base stay
    stable across reseeds — only the activity refreshes.
- `app/core/config.py` — four new settings: `DEMO_RESEED_TOKEN`,
  `DEMO_LOGIN_EMAIL`, `DEMO_LOGIN_PASSWORD`, `DEMO_CLINIC_NAME`.
- `app/integrations/supabase_admin.py` — two new helper functions
  (`find_user_id_by_email`, `get_or_create_user_with_password`) so the demo
  login can be created with a known password and no email-confirmation step.
- `app/main.py` — registers the new router (two lines added).

**No database migration needed** — this doesn't add any tables or columns,
just rows in your existing ones.

**Frontend**
- `app/demo/page.tsx` — new public page. Shows what's inside the demo, the
  clinic name, and the login email/password with one-click copy buttons.
- `app/login/page.tsx` — one new line linking to `/demo` ("Want to see a
  live demo first?").

## 2. Deploying it

1. Copy the files from this delivery into your repo at the paths named
   above (new files go in as new files; `config.py`, `supabase_admin.py`,
   `main.py`, and `login/page.tsx` replace your existing ones).
2. On Railway, add one new environment variable to the backend service:

   ```
   DEMO_RESEED_TOKEN=<any long random string you make up>
   ```

   This is the only one you must set — leaving it unset disables the
   reseed endpoint entirely (it returns 503), so there's no risk of it
   being live-but-unprotected by accident. Keep this value private; it's
   not a `NEXT_PUBLIC_*` var and never reaches the frontend.

   Optional overrides (sensible defaults exist if you skip these):
   ```
   DEMO_LOGIN_EMAIL=demo@auradesk.ai
   DEMO_LOGIN_PASSWORD=AuraDeskDemo2026!
   DEMO_CLINIC_NAME=Glow Aesthetic Studio
   ```

3. Commit and push — Railway and Vercel will redeploy automatically.
4. Run the reseed once (see below) to actually create the demo data —
   nothing exists until you do this the first time.

## 3. Reseeding before a demo

Run this once right after deploying, and again before any client call
that's more than a day or two after the last reseed — the dashboard's
"today" numbers are computed live, so a stale seed will show yesterday's
(or last month's) activity as "today."

```bash
curl -X POST https://<your-railway-backend-url>/api/v1/demo/reseed \
  -H "X-Demo-Token: <your DEMO_RESEED_TOKEN value>"
```

A successful response looks like:
```json
{
  "status": "ok",
  "clinic_id": "...",
  "counts": {
    "patients": 10, "conversations": 10, "messages": 33,
    "calls": 2, "escalations": 1, "appointments": 8,
    "services": 6, "knowledge_base_articles": 9
  }
}
```

The login email and password never change across reseeds — only the
clinic's activity refreshes. Share `https://<your-vercel-frontend-url>/demo`
with the prospect; they can view and copy the credentials themselves.

## 4. What's actually inside — so you can narrate it

**The clinic**: Glow Aesthetic Studio, a med spa in Austin, TX. Owner
persona "Jordan Reyes." AI Employee is named "Aura."

**Services** (6): Botox ($450), Lip Filler ($650), HydraFacial ($199),
Laser Hair Removal — Underarms ($120), Chemical Peel ($175), Microneedling
with PRP ($450).

**Knowledge base** (9 articles): pricing, hours, cancellation policy,
consultation requirements, walk-ins, and service-specific FAQs — this is
what Aura answers from automatically, with no hallucination risk.

**Patients & conversations** (10 patients, 10 conversations spread across
today / yesterday / the last 5 days, across voice, SMS, web chat, Messenger,
and Instagram):

- **Today**: Sophia Chen calls and books Botox; Olivia Martinez texts and
  books laser hair removal; Mia Johnson texts a quick hours question;
  Emma Larson asks about filler pricing on web chat and goes quiet (a
  missed lead — a good moment to point at "missed leads" on the dashboard);
  Harper Wilson asks a policy question on Messenger.
- **Yesterday**: Ava Thompson books a HydraFacial via Messenger; Isabella
  Rodriguez asks about microneedling on Instagram and doesn't follow up.
- **2 days ago**: Charlotte Davis is unhappy about filler results and
  demands a refund — Aura escalates it to staff immediately. Good moment
  to show the Escalations page and how it protects the clinic from a bad
  automated response to a sensitive situation.
- **4-5 days ago**: Amelia Garcia calls to reschedule; Evelyn Brown asks
  about walk-ins on Instagram.

**Appointments** (8, mixing every status so each page has something to
show): 2 freshly booked today (Botox, laser), 1 confirmed for next week
(HydraFacial), 1 completed (filler), 1 booked manually by staff
(microneedling), 1 no-show (HydraFacial), 1 completed (Botox), 1 canceled
(filler).

**Dashboard numbers right after a reseed** (today's date, your time zone
may shift these by an hour but the shape holds): 1 call today, 2 texts
today, 2 chats today, 2 booked today, 1 missed lead today, **$570 revenue
today**, 4 upcoming appointments, **~30% 7-day conversion rate**.

**Billing**: shows an active "Professional" plan subscription — this is
what a paying customer's billing page looks like, not an empty trial.

## 5. A few things worth saying out loud on the call

- "This isn't a mockup — you're logged into the same product your clinic
  would actually run on."
- Point at a specific conversation (Sophia's Botox booking) and walk
  through it message-by-message, then show the matching appointment on
  the Appointments page — "the AI did this end-to-end, no staff time."
- Show the Charlotte Davis escalation and explain: "Aura knows what it
  doesn't know — anything about refunds, complaints, or medical complications
  gets handed to a human immediately, it never tries to resolve that itself."
- Show the Knowledge Base page and explain that whatever's answered there
  is answered from the clinic's own approved content, not improvised.
