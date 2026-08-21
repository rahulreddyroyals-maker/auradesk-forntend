# Incident Response

**Current state: no formal incident response plan exists yet.** This
document is a starting skeleton, not a completed policy — a real IR
plan needs sign-off from whoever will own compliance for AuraDesk as a
company, not just an engineering artifact.

## What HIPAA requires (45 CFR §164.308(a)(6))

A documented process to identify, respond to, mitigate, and document
security incidents — including a specific Breach Notification Rule
process if PHI is actually exposed (45 CFR Part 164 Subpart D), which
has strict timelines (generally: affected individuals within 60 days of
discovery; HHS notified; media notification if 500+ individuals in a
state/jurisdiction are affected).

## Minimum skeleton (to be filled in with real names/contacts before production)

1. **Detection**: Sentry (referenced in original architecture, not yet
   wired up in this codebase) would be the primary error-detection
   surface. No PHI should ever appear in a Sentry event — enforced via
   the logging redaction work in this pass, but not yet verified against
   an actual Sentry integration since one isn't wired up yet.
2. **Triage**: designate a specific person (not yet named) responsible
   for triaging any reported security concern within 24 hours.
3. **Containment**: for a suspected cross-tenant data leak, the fastest
   containment step is disabling the affected endpoint(s) via a feature
   flag or deployment rollback — no such flag mechanism exists yet in
   this codebase.
4. **Notification**: if PHI is confirmed exposed, the Breach
   Notification Rule timeline above applies. This requires legal
   counsel, not just engineering — flagged as a LEGAL/ADMINISTRATIVE
   REQUIREMENT in `HIPAA_READINESS_STATUS.md`.
5. **Post-incident**: root-cause writeup, and a check of whether the
   audit log (see `ACCESS_CONTROL.md`) captured enough detail to
   determine what was actually accessed.

## What's NOT yet implemented

- No named incident response owner or escalation contact list.
- No Sentry (or equivalent) integration wired up in this codebase yet.
- No feature-flag/kill-switch mechanism for rapid containment.
- No breach notification template/process.

This entire document should be treated as a first draft for a human
compliance owner to complete, not a finished policy.
