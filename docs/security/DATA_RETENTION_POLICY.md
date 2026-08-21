# Data Retention Policy

**Current state: no automated retention/deletion exists.** Everything
is kept indefinitely today. This document defines the target policy;
implementing the automated enforcement of it is listed as NOT
IMPLEMENTED in `HIPAA_READINESS_STATUS.md`.

## Recommended retention periods

| Data type | Recommended retention | Rationale |
|---|---|---|
| Conversations / messages | 6 years from creation | Matches HIPAA's general 6-year documentation retention expectation (45 CFR §164.316) as a reasonable default — confirm against your specific state requirements, which can be longer |
| Call audio (if ever recorded — not currently) | Not stored at all today; if implemented later, same 6-year default | No recordings currently persist — audio is processed in-memory during the call only |
| SMS/webhook raw payloads | Not separately stored beyond the `messages` row | N/A |
| Lead/patient records for people who never became patients | 2 years of inactivity, then flagged for deletion review | Balances "AI Employee recovers missed leads" against not indefinitely hoarding contact info for people who never engaged |
| Audit logs | 6 years | Same HIPAA documentation-retention reasoning |
| Deleted user/tenant data | 30-day soft-delete window, then hard delete | Gives recovery time for accidental deletion without indefinite retention |
| Stripe billing records | Per Stripe's own retention (not PHI, out of this policy's scope) | N/A |

## What's NOT yet implemented

- No scheduled job purges old conversations/messages.
- No "export and delete" workflow for a patient who requests their data
  be removed (a real right under many state privacy laws, and good
  practice regardless of HIPAA specifics).
- No tenant offboarding deletion workflow (what happens to a clinic's
  data if they cancel).

## Recommended next engineering step

A `app/workers/retention_cleanup.py` job, structured like
`followup_scheduler.py`, run on the same cron/Task Scheduler cadence,
that soft-deletes (sets a `deleted_at` timestamp, doesn't hard-delete
immediately) records past their retention window, with a separate
hard-delete pass after the recovery window. Not built this pass —
flagged as the top follow-up item after the BAA/vendor-plan work.
