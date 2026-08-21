# Architecture Security Audit

Full inspection of the AuraDesk codebase as it exists today, mapping
every place sensitive data can enter, leave, or be stored.

## System overview

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind. Talks to
  the backend via a REST API using a Supabase-issued JWT.
- **Backend**: FastAPI (Python), synchronous SQLAlchemy ORM against
  Postgres.
- **Database**: Supabase-hosted Postgres. As of this audit, on
  whatever plan was used during initial project setup (verify — HIPAA
  requires Team/Enterprise + HIPAA add-on, see `THIRD_PARTY_VENDOR_MATRIX.md`).
- **Auth**: Supabase Auth (email/password), JWTs signed ES256 (asymmetric,
  verified via JWKS) or HS256 (legacy), carrying custom `clinic_id`/`role`
  claims via a Postgres Auth Hook.
- **Multi-tenancy**: every table keyed by `clinic_id`. Enforced at the
  application layer (every query filters by it — audited, confirmed
  clean) and, as of the RLS-hardening pass, at the database layer for
  a restricted connection role (`auradesk_app`) — see `ACCESS_CONTROL.md`.

## Where sensitive data enters the system

| Entry point | Data received | File |
|---|---|---|
| Web chat test console | Patient message text | `app/api/v1/ai_employee.py` (`/test-message`) |
| SMS webhook | Phone number, message text | `app/api/v1/sms.py` |
| Voice webhook + Media Stream | Phone number, live audio | `app/api/v1/calls.py`, `app/orchestrator/voice_pipeline.py` |
| Messenger/Instagram webhook | PSID/IGSID, message text | `app/api/v1/social.py` |
| Manual patient entry | Name, phone, email | `app/api/v1/patients.py` |
| Onboarding | Clinic name, owner name, email (via Supabase Auth) | `app/api/v1/onboarding.py` |
| Team invite | Staff email | `app/api/v1/team.py` |

## Where sensitive data leaves the system (to third parties)

| Destination | What's sent | Purpose |
|---|---|---|
| Groq | Conversation text (last ~10 turns), system prompt, audio (voice) | LLM reasoning, Whisper transcription |
| Cartesia / ElevenLabs | AI-generated reply text | Text-to-speech |
| Twilio | Phone numbers, SMS/voice content | Transport |
| Meta | Message text, PSID/IGSID | Transport (Messenger/Instagram) |
| Stripe | Clinic name, clinic email, billing metadata | Subscription billing — **never patient data** |
| Supabase Admin API | Staff email | Sending invite emails |

## Where sensitive data is stored (at rest)

All in the Supabase Postgres database:

- `patients` — name, phone, email, lifecycle stage, tags, external
  channel IDs
- `conversations` / `messages` — full conversation content, including
  whatever the patient said (which can include treatment questions —
  this is the primary PHI-risk table)
- `appointments` — patient + service (treatment type) + time
- `calls` — Twilio call SID, duration, **recording_url column exists
  in the schema but nothing currently populates it** — no call
  recordings are actually stored today
- `escalations` — reason text (can reference a health concern)

## Logging

Reviewed every `print()`/log statement in the backend. Current state:
mostly safe (logs exception messages and IDs, not conversation
content), but not yet using structured, redaction-enforced logging —
see `AI_SAFETY.md` and the logging changes in this pass for what's been
added.

## Background jobs

`app/workers/followup_scheduler.py` — reads patient phone numbers and
sends a fixed-text SMS. No patient-specific content in the message
itself (a generic check-in), reducing exposure.

## Admin / privileged access

Two Postgres connection roles as of this pass: a restricted
`auradesk_app` role (RLS-enforced, used for normal requests) and an
admin role (bypasses RLS, used only for migrations and the small set of
bootstrapping operations that structurally require it — see
`ACCESS_CONTROL.md`). No separate application "admin panel" exists yet;
Supabase's own dashboard is the only true admin surface, and access to
it is Supabase-account-level, outside this codebase's control.

## What this audit did NOT find

- No secrets committed to the repository (checked `.env` is gitignored,
  no hardcoded API keys in source).
- No `NEXT_PUBLIC_`-prefixed environment variables carry a secret (only
  Supabase's anon key and the public API base URL, both meant to be
  public).
- No SQL string concatenation — all queries go through SQLAlchemy's
  parameterized query builder.
