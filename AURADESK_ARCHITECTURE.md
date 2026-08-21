# AuraDesk — System Architecture

**Your 24/7 AI Employee for Med Spas**

---

## 1. Product Framing

AuraDesk is not a chatbot bolted onto a website. It is a **multi-channel AI staff member** with:

- A single **conversation brain** (shared context, memory, tools) regardless of channel
- A **calendar hand** (books/reschedules real appointments)
- A **CRM hand** (updates patient records)
- **Judgment** (knows when to escalate instead of guessing)
- An **employee record** the clinic can configure (name, voice, personality, hours, escalation rules) — this is the "AI Employee" entity in the data model, not just a prompt string

Everything downstream flows from that framing: one `Conversation` object per customer thread, independent of whether it started as a phone call, SMS, or IG DM, so a lead who calls then texts sees continuity.

---

## 2. Multi-Tenancy Model

Every clinic (tenant) is a `clinic` row. All data is scoped by `clinic_id` with **Postgres Row-Level Security (RLS)** enforced at the Supabase layer — not just application-layer checks. This is non-negotiable for a HIPAA-adjacent product handling patient data: the database itself refuses cross-tenant reads even if application code has a bug.

- `clinic_id` is embedded in the Supabase Auth JWT as a custom claim
- Every table (except global lookup tables) has `clinic_id NOT NULL` + RLS policy `USING (clinic_id = auth.jwt() -> 'clinic_id')`
- Staff belong to exactly one clinic (v1); multi-location support is a `clinic_group_id` extension point we design for now but don't build yet

---

## 3. Data Model (Core Schema)

```
clinics
  id, name, slug, timezone, phone_number, address, hours_json,
  branding_json (logo, colors), status (trial/active/paused/canceled),
  created_at

staff (clinic employees who use the dashboard)
  id, clinic_id, user_id (fk -> supabase auth.users), name, role
  (owner/admin/front_desk), phone, notification_prefs_json, created_at

ai_employees (the configurable "AI staff member" per clinic)
  id, clinic_id, name, voice_id, personality_prompt,
  escalation_rules_json, active_hours_json, status, created_at

patients (clinic's customers/leads)
  id, clinic_id, first_name, last_name, phone, email,
  source_channel, tags[], lifecycle_stage (lead/patient/member),
  created_at, last_contacted_at

conversations (channel-agnostic thread)
  id, clinic_id, patient_id, channel (voice/sms/web_chat/messenger/instagram),
  status (active/escalated/resolved/abandoned), started_at, ended_at,
  ai_handled (bool), escalated_to_staff_id, outcome
  (booked/rescheduled/faq_only/no_action/lost)

messages (every turn within a conversation, any channel)
  id, conversation_id, role (patient/ai/staff/system), channel,
  content, audio_url, transcript_confidence, tool_calls_json,
  created_at

calls (voice-specific metadata, 1:1 with a conversation)
  id, conversation_id, twilio_call_sid, direction, duration_seconds,
  recording_url, transcript_id, sentiment, created_at

appointments
  id, clinic_id, patient_id, conversation_id, service_id,
  provider_staff_id, start_time, end_time, status
  (booked/confirmed/rescheduled/canceled/completed/no_show),
  booked_by (ai/staff), created_at

services (Botox, Fillers, Laser, Hydrafacial, PRP, Microneedling, ...)
  id, clinic_id, name, category, duration_minutes, price_cents,
  description, active

memberships
  id, clinic_id, name, price_cents, billing_interval, benefits_json

knowledge_base_articles (FAQ / policy source-of-truth for the AI)
  id, clinic_id, category, question, answer, embedding vector(1536),
  source (manual/imported), updated_at

escalations
  id, conversation_id, clinic_id, reason, urgency, notified_staff_ids[],
  resolved (bool), resolved_by, created_at

integrations (per-clinic channel credentials/config)
  id, clinic_id, type (twilio/fb_messenger/instagram/calendar/ehr),
  status, config_json (encrypted), connected_at

usage_events (for analytics + billing metering)
  id, clinic_id, event_type, metadata_json, created_at

subscriptions / invoices (Stripe mirror tables)
  ...
```

Key design choices:
- **`conversations` is the spine.** Calls, SMS threads, and chat sessions are all just `messages` under a `conversation`, which is how "answer phone → follow up by SMS → book" stays one coherent thread.
- **`knowledge_base_articles.embedding`** — pgvector column for RAG. The AI Employee never free-hallucinates pricing/policy; it retrieves grounded KB chunks and cites them internally before answering. This is the mechanism behind "never hallucinates."
- **`tool_calls_json` on messages** gives a full audit trail of every booking/reschedule/lookup the AI performed — critical for trust and for debugging a "why did the AI say that" support ticket.

---

## 4. AI Employee Architecture

### 4.1 Voice pipeline (phone calls)

```
Twilio Voice (inbound call, media stream)
   ↓ (WebSocket audio stream)
Groq Whisper (streaming STT)
   ↓ (partial + final transcripts)
Orchestrator (FastAPI, per-call session state machine)
   ↓
Groq Llama (reasoning + tool calling)
   ↓
Tool Layer: check_availability / book_appointment / reschedule_appointment /
            lookup_kb / lookup_patient / create_escalation / send_sms_followup
   ↓
Cartesia TTS (streaming) — fallback: ElevenLabs on Cartesia error/timeout
   ↓
Twilio Voice (stream audio back)
   ↓
On call end: persist Conversation + Messages + Call record, trigger post-call summary + follow-up SMS if applicable
```

Latency budget matters here — for a natural-feeling phone call we target <800ms round trip per turn (STT partial → LLM first token → TTS first audio chunk), which is why STT and TTS are both streaming, not batch.

### 4.2 Text channels (SMS / Web Chat / Messenger / Instagram)

All four normalize into the same `Conversation`/`Message` model via channel-specific adapters:

```
Twilio SMS webhook ─┐
Web Chat (WS/SSE)   ─┼─► Channel Adapter → normalize → Orchestrator (same brain as voice, minus audio) → Channel Adapter → reply
Meta Messenger webhook ─┤        (text-only turns skip STT/TTS, same tool layer + KB)
Instagram DM webhook ─┘
```

Reusing one orchestrator for voice and text (rather than separate logic per channel) is what makes this an "AI employee" rather than four disconnected bots — the personality, KB, and escalation rules are configured once per clinic.

### 4.3 Guardrails ("never reveals prompts, never hallucinates")

- System prompt is never echoed; a dedicated pre-response filter strips any leaked instruction-like content before it's spoken/sent.
- Every factual claim about pricing/policy must resolve through a KB tool call — the model is instructed (and structurally constrained via tool-required responses for factual questions) not to answer pricing/medical questions from parametric memory.
- A separate lightweight "safety/scope classifier" runs on each inbound message to flag medical-advice requests, complaints, or emergencies for immediate escalation rather than an AI-generated answer.

### 4.4 Escalation

Rules-based + model-flagged triggers (angry sentiment, medical question outside scope, repeated failed intent resolution, explicit "talk to a person") → `escalations` row created → staff notified via SMS/push/dashboard per their `notification_prefs_json` → conversation flagged `escalated` until a staff member responds.

---

## 5. Backend (FastAPI) Module Layout

```
/backend
  /app
    /api/v1
      /calls          (Twilio voice webhooks, media stream handler)
      /sms             (Twilio SMS webhooks)
      /chat            (web chat WS/SSE endpoint)
      /messenger       (Meta webhook)
      /instagram       (Meta webhook)
      /appointments    (CRUD, availability)
      /patients        (CRUD, search)
      /knowledge_base  (CRUD, embedding sync)
      /ai_employee     (config CRUD)
      /analytics       (dashboard metrics)
      /billing         (Stripe webhooks, subscription mgmt)
      /auth            (Supabase session helpers)
    /core
      config.py, security.py, rls.py, logging.py
    /orchestrator
      session.py        (per-conversation state machine)
      tools.py           (tool definitions + execution)
      voice_pipeline.py  (STT/TTS streaming glue)
      guardrails.py
    /integrations
      twilio_client.py, groq_client.py, cartesia_client.py,
      elevenlabs_client.py, meta_client.py, stripe_client.py
    /models          (SQLAlchemy models mirroring schema above)
    /schemas         (Pydantic request/response models)
    /services        (business logic layer between API and models)
    /db
      session.py, migrations (Alembic)
    /workers
      followup_scheduler.py, escalation_notifier.py, kb_embedder.py
  requirements.txt / pyproject.toml
```

Rationale: **API routers stay thin**; all logic lives in `/services` and `/orchestrator` so the same booking logic is reachable from a voice call, an SMS, and the dashboard's manual "book for patient" button.

---

## 6. Frontend (Next.js) Structure

```
/frontend
  /app
    /(marketing)/page.tsx                 → Landing page
    /(app)/dashboard
    /(app)/inbox                          → unified conversation list (all channels)
    /(app)/calls
    /(app)/sms
    /(app)/chat
    /(app)/appointments
    /(app)/calendar
    /(app)/knowledge-base
    /(app)/analytics
    /(app)/patients
    /(app)/ai-employee                    → configure the AI (personality, voice, hours)
    /(app)/conversation-history/[id]
    /(app)/integrations
    /(app)/logs
    /(app)/notifications
    /(app)/settings
    /(app)/billing
    /(app)/team
  /components
    /ui        (shadcn primitives)
    /shared    (AppShell, Sidebar, TopBar, CommandPalette)
    /inbox, /calls, /appointments, /analytics, /ai-employee ... (feature components)
  /lib
    supabase-client.ts, api-client.ts, hooks/, types/ (generated from backend schemas)
```

Design system: white/gold/black, glassmorphism cards on a soft off-white background (not heavy blur-everywhere — used selectively for the AI Employee "live" panel and modals), Inter or a similar geometric sans for UI text, a serif or refined sans for marketing headlines to hit the "luxury" note in the logo. Dark mode mirrors the palette with charcoal/black base and gold accents preserved.

---

## 7. Cross-Cutting Concerns

- **Auth**: Supabase Auth, clinic-scoped JWT claims, role-based UI gating (owner/admin/front_desk).
- **Realtime**: Supabase Realtime (or WS) pushes new inbox messages/escalations to the dashboard live — this is what makes staff trust the AI ("I can see it working").
- **Observability**: Sentry on both frontend and backend; PostHog for product analytics (funnel: lead → AI conversation → booked appointment → revenue).
- **Billing**: Stripe subscriptions, usage metering table feeds overage/plan-limit logic.
- **Compliance posture**: treat patient phone/PII as sensitive from day one — encryption at rest (Supabase default), RLS everywhere, audit log via `tool_calls_json` + `usage_events`, no PHI in Sentry breadcrumbs (scrub before send).

---

## 8. Phased Build Roadmap

We build in vertical slices, each shippable and demoable — not "all backend, then all frontend."

| Phase | Scope | Outcome |
|---|---|---|
| **0** | Monorepo scaffold, DB schema + Alembic migrations, Supabase project config, RLS policies, auth flow, base Next.js app shell with nav for all pages (empty states) | You can log in, see the shell, tenant isolation is provable |
| **1** | Knowledge Base + AI Employee config CRUD, Patients + Appointments CRUD, Services/Memberships CRUD | Clinic can set up their data manually before AI touches it |
| **2** | Web Chat channel end-to-end (orchestrator + KB RAG + booking tool calls) — cheapest channel to prove the brain works | Working AI employee via chat widget, unified Inbox showing it |
| **3** | SMS channel via Twilio (reuses orchestrator) + follow-up automation worker | Two-channel AI employee, automatic re-engagement |
| **4** | Voice pipeline: Twilio Voice + Groq Whisper streaming + Cartesia TTS + ElevenLabs fallback | Phone calls answered and booked by AI |
| **5** | Messenger + Instagram adapters, Escalation system + staff notifications | Full channel coverage, human-in-the-loop safety net |
| **6** | Analytics dashboard, Billing/Stripe, Team management, Logs, polish/animations, landing page | Sellable, $2k/mo-grade product |

Each phase = real, working, non-toy code — not stubs — but scoped narrowly enough to review and correct course before compounding architecture decisions.

---

## 9. Open Decisions Before Phase 0

A few things worth deciding now rather than defaulting silently:
- **Calendar system**: build our own scheduling engine (fits `appointments` table above) vs. sync to Google Calendar/Cal.com per clinic. Affects Phase 1 scope significantly.
- **EHR/PMS integration** (e.g. Vagaro, Boulevard, Mindbody — common in med spas): out of scope for MVP, or a stub integration point in `integrations` table now?
- **Voice provider order**: confirmed Cartesia primary / ElevenLabs fallback — keep as-is?
