# Backup & Recovery

**Honest scope**: this document describes what's actually configured,
not an aspirational target. AuraDesk's database runs on Supabase, which
provides platform-level backups — those are Supabase's responsibility
and documented on their own site; this project has not configured
anything beyond Supabase's defaults, and has not verified or tested a
restore.

## What's true today

- Database backups: whatever Supabase's plan-level default is (varies
  by plan — Free/Pro tiers have more limited point-in-time recovery
  windows than Team/Enterprise). **Not independently verified as part of
  this audit** — check your actual Supabase project's Backups settings
  page for the current configured schedule and retention.
- No application-level backup exists outside of Supabase's own.
- No disaster-recovery drill has been performed.
- No documented RPO (Recovery Point Objective) or RTO (Recovery Time
  Objective) — these numbers should not be published until they've been
  tested, not assumed.

## What this means for HIPAA readiness

HIPAA's Security Rule requires a documented, tested data backup and
disaster recovery plan (45 CFR §164.308(a)(7)). "Supabase probably backs
things up" is not that — it needs to be: (1) explicitly verified against
your actual plan's backup configuration, (2) tested with an actual
restore at least once, (3) documented with real RPO/RTO numbers derived
from that test, not guessed.

## Recommended next step

Before onboarding real patient data: log into the Supabase dashboard,
confirm the project's backup schedule and retention window, perform a
test restore into a separate project, time how long it takes, and
replace this document's placeholder language with real, measured
numbers.
