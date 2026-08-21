# Third-Party Vendor Matrix

Verified against each vendor's own current documentation as of this
audit (August 2026). Vendor postures change — re-verify before
contracting, especially given how fast this space is moving.

## Groq (LLM reasoning + Whisper transcription)

- **Data received**: conversation text, system prompt, audio (for
  transcription)
- **PHI exposure**: high — this is where the AI actually reasons about
  what the patient said
- **BAA**: **Available.** Groq publishes a standard Business Associate
  Addendum at `console.groq.com/docs/legal/customer-business-associate-addendum`.
- **Required plan**: not identified as tier-restricted in public docs —
  verify current terms directly with Groq before contracting.
- **Status**: **ELIGIBLE, NOT YET SIGNED.**
- **Recommended action**: sign the BAA before any real patient data
  flows through this integration.

## Twilio (SMS + Voice transport)

- **Data received**: phone numbers, SMS/voice content, call audio
  (streamed, not currently recorded/stored by AuraDesk)
- **PHI exposure**: high — carries the actual conversation
- **BAA**: **Available**, but only for Twilio's designated HIPAA-eligible
  products (SMS, Voice, Video, SendGrid, select Flex), and only on
  **Security or Enterprise Edition** accounts — not on trial or standard
  accounts. Contact Twilio Sales to execute.
- **Status**: **NOT APPROVED FOR PHI as currently configured** (no
  Twilio account has been set up yet at all, per project history — when
  one is, it needs to be Security/Enterprise Edition with a signed BAA).
- **Recommended action**: when setting up the production Twilio
  account, go through Sales for a HIPAA-eligible Edition, not a
  self-serve trial signup.

## Cartesia (primary TTS)

- **Data received**: AI-generated reply text (not the patient's
  original message)
- **PHI exposure**: moderate — reply text can reference treatment
  details the AI decided to say back
- **BAA**: **Available** via enterprise contract, per Cartesia's own
  documentation (SOC 2 Type II, PCI Level 1, HIPAA, with BAA as an
  enterprise contract option).
- **Status**: **ELIGIBLE, NOT YET SIGNED** (current integration uses
  the public API, not an enterprise/BAA-covered contract).
- **Recommended action**: move to an enterprise contract with signed
  BAA before production PHI use.

## ElevenLabs (fallback TTS)

- **Data received**: same as Cartesia — AI reply text, used only if
  Cartesia's call fails
- **PHI exposure**: moderate, same reasoning as Cartesia
- **BAA**: **Available**, but only on **Business or Enterprise tiers**,
  and requires **Zero Retention Mode** to be explicitly enabled.
- **Status**: **NOT APPROVED FOR PHI as currently configured** (default
  API tier, Zero Retention Mode not configured).
- **Recommended action**: if keeping ElevenLabs as fallback, upgrade to
  a qualifying tier, enable Zero Retention Mode, and sign the BAA.
  Otherwise, consider dropping the fallback until this is in place.

## Supabase (database + auth)

- **Data received / stores**: everything — patients, conversations,
  messages, appointments, all of it
- **PHI exposure**: highest of any vendor — this is the system of
  record
- **BAA**: **Available**, but only on **Team ($599/mo class pricing) or
  Enterprise plans, with the HIPAA add-on enabled** (reported around
  $200-350/mo on top of the base plan in third-party sources — verify
  exact current pricing directly with Supabase, don't rely on
  third-party figures for a number this consequential). **Free and Pro
  plans do not support HIPAA at any configuration.**
- **Status**: **NOT APPROVED FOR PHI as currently configured** — the
  project was set up on what is almost certainly the Free or Pro tier.
  This is the single most urgent vendor item to fix before any real
  patient data touches this system, since it's also the vendor with the
  most exposure.
- **Recommended action**: upgrade to Team or Enterprise, enable the
  HIPAA add-on, sign the BAA, and confirm the project is reconfigured
  as "High Compliance" per Supabase's own HIPAA Projects documentation
  before real data is entered.

## Meta (Messenger + Instagram transport)

- **Data received**: message text, sender PSID/IGSID
- **PHI exposure**: same as SMS/voice — carries real conversation
- **BAA**: **Not available. Meta does not sign BAAs for Messenger,
  Instagram, or any consumer messaging surface, on any plan, for any
  price.** Confirmed via HIPAA Journal, multiple compliance-focused
  sources, and Meta's own advertising/healthcare guidance (which
  explicitly states Meta won't sign BAAs even for ad products).
- **Status**: **NOT APPROVED FOR PHI. PERMANENT, NOT A CONFIGURATION
  GAP.**
- **Recommended action**: do not treat this as "fix later." Either (a)
  exclude Messenger/Instagram from any clinic's PHI-handling workflow
  by product design and contract terms, or (b) restrict what the AI
  Employee is permitted to discuss on these channels (implemented this
  pass — see `AI_SAFETY.md`) and make clinics using these channels
  aware, in writing, that they must not conduct PHI-bearing
  conversations there.

## Stripe (billing)

- **Data received**: clinic name, clinic billing email, subscription
  status — **never patient data**, by design (Stripe only processes the
  *clinic's own subscription payment to AuraDesk*, not anything
  patient-related)
- **PHI exposure**: none, by architecture
- **BAA**: not evaluated — out of scope, since this integration never
  touches PHI regardless of Stripe's own HIPAA posture
- **Status**: **N/A — no PHI exposure to evaluate.**

## Vercel / Railway (hosting — referenced in the original architecture doc, not yet deployed)

Not yet evaluated, since the application isn't deployed to either as of
this audit — only run locally. **Before deploying to either for
production use, this same BAA-verification process must be repeated**;
do not assume either is HIPAA-eligible without checking current
official documentation at deployment time.
