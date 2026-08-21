# PHI Data Flow

Traces patient data through the system for each channel. "Is PHI
possible?" is answered generously — a med spa AI Employee's whole job
is discussing treatments, which makes almost everything here
PHI-adjacent the moment it's tied to an identifiable person.

## Voice call

```
Caller (phone)
  ↓ audio
Twilio (transport)                    Encryption: TLS in transit. BAA: available, not signed. Eligible plan: Security/Enterprise Edition, not current trial account.
  ↓ 8kHz mulaw audio, WebSocket
AuraDesk backend (transient, in-memory buffer during the call)
  ↓ WAV audio
Groq Whisper (transcription)          Encryption: TLS in transit. BAA: available, not signed. Retention: not verified — ask Groq for their retention policy under BAA terms before production use.
  ↓ transcript text
Groq LLM (reasoning)                  Same vendor/BAA status as above. Sees: system prompt + last ~10 conversation turns + this transcript.
  ↓ reply text
Cartesia (primary) / ElevenLabs (fallback) TTS   Encryption: TLS. BAA: available (Cartesia: enterprise contract; ElevenLabs: Business/Enterprise + Zero Retention Mode required), neither signed yet.
  ↓ synthesized audio
Twilio → Caller
  ↓ (in parallel)
Supabase Postgres (conversation + message rows stored)   Encryption: TLS in transit, at-rest encryption per Supabase's platform default. BAA + HIPAA add-on: available, not signed/enabled.
```

Stored: full transcript (as `messages` rows), call metadata (`calls`
row — no recording audio is persisted). Retention: indefinite today —
see `DATA_RETENTION_POLICY.md` for what's recommended.

**If Twilio/Groq/Cartesia become unavailable mid-call**: the call fails
ungracefully today — no documented fallback-to-human path exists yet.
Flagged as a gap.

## SMS

Same Twilio/Groq path as voice, minus the audio/TTS steps. Message text
stored verbatim in `messages`.

## Web chat (test console)

Entirely internal — clinic owner types as a test patient, hits the same
orchestrator, no third-party transport vendor involved (just Groq for
the LLM). Lowest-exposure channel.

## Messenger / Instagram

```
Patient (Messenger/Instagram app)
  ↓
Meta (transport)     Encryption: TLS in transit (Meta's platform). BAA: Meta will not sign one, on any plan, ever — confirmed via multiple current sources. NOT APPROVED FOR PHI.
  ↓
AuraDesk backend → Groq → same as above → reply → Meta → Patient
```

**This is the one channel that cannot be brought into HIPAA compliance
by upgrading a plan or signing a contract — the vendor refuses BAAs
structurally.** As of this pass, the AI Employee's system prompt is
restricted on these two channels to avoid discussing specific
treatment/health details (see `AI_SAFETY.md`) — this reduces exposure
but does not eliminate it, since a patient can still type anything they
want, including health information, into Messenger. The only complete
fix is a contractual/product decision: either don't offer
Messenger/Instagram to clinics who will discuss PHI there, or ensure
contractually that clinics using these channels only use them for
non-PHI purposes (hours, general inquiries) and route anything
health-specific to a channel that can carry PHI.

## Third-party vendor summary

See `THIRD_PARTY_VENDOR_MATRIX.md` for the full table. Short version:
every vendor except Meta is *eligible* for a BAA; **none currently has
one signed**.
