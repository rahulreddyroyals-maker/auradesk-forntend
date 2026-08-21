# AuraDesk Security & HIPAA Readiness Documentation

This directory is the honest source of truth for AuraDesk's security
posture and HIPAA readiness. It follows one rule throughout: **no
compliance claim appears here without evidence**. Where something is
implemented, it says so and how it was verified. Where something
depends on a vendor, a contract, or a legal decision outside this
codebase, it says that plainly instead of papering over it.

**AuraDesk is not "HIPAA compliant."** No software product can claim
that in isolation — HIPAA compliance is a property of an organization's
whole program (contracts, administrative safeguards, workforce training,
risk analysis), not a checkbox a codebase ticks. What this documentation
set describes is AuraDesk's **technical HIPAA readiness**: the
engineering safeguards in place, and exactly what still depends on
business decisions (signing BAAs, upgrading vendor plans) before real
patient data should touch this system.

## Read these in order

1. [`ARCHITECTURE_SECURITY_AUDIT.md`](./ARCHITECTURE_SECURITY_AUDIT.md) — what the system is, and everywhere sensitive data can enter, move, or rest.
2. [`PHI_DATA_FLOW.md`](./PHI_DATA_FLOW.md) — step-by-step trace of patient data from a phone call/text/message to storage, with vendor exposure at each step.
3. [`THIRD_PARTY_VENDOR_MATRIX.md`](./THIRD_PARTY_VENDOR_MATRIX.md) — every vendor, verified BAA availability, and current approval status.
4. [`DATA_RETENTION_POLICY.md`](./DATA_RETENTION_POLICY.md) — what's kept, for how long, and the deletion story.
5. [`ACCESS_CONTROL.md`](./ACCESS_CONTROL.md) — authentication, authorization, RBAC, tenant isolation.
6. [`AI_SAFETY.md`](./AI_SAFETY.md) — data minimization, prompt injection defenses, tool authorization, medical-scope guardrails.
7. [`INCIDENT_RESPONSE.md`](./INCIDENT_RESPONSE.md) — what happens if something goes wrong.
8. [`BACKUP_AND_RECOVERY.md`](./BACKUP_AND_RECOVERY.md) — backup posture, honestly scoped to what's actually configured.
9. [`SECURITY_TESTING.md`](./SECURITY_TESTING.md) — what's covered by `/backend/tests/security/`, and what isn't yet.
10. [`HIPAA_READINESS_STATUS.md`](./HIPAA_READINESS_STATUS.md) — the master checklist, one line per requirement, honestly classified.

## The single most important finding

**No Business Associate Agreement is currently signed with any vendor.**
Every vendor this system uses is *eligible* to sign one (except Meta —
see below), but eligibility is not a signed contract. Until BAAs are
signed and the relevant vendor plans are upgraded to their HIPAA-eligible
tiers, **this system should only be used with synthetic test data, never
real patient information.**

**Meta (Messenger, Instagram) will not sign a BAA under any
circumstances, on any plan — confirmed across multiple independent,
current sources.** This is not a temporary gap to close later; it's a
permanent constraint. See `AI_SAFETY.md` for how the AI Employee's
behavior is restricted on these two channels as a result.
