# Security Testing

`/backend/tests/security/` — 22 automated tests, all passing as of this
pass. Run with:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m pytest tests/security/ -v
```

## What's covered

| Category | File | What it actually checks |
|---|---|---|
| Cross-tenant access / IDOR | `test_cross_tenant_isolation.py` | Clinic A cannot fetch, list, or delete Clinic B's patient by ID — exercises the real query shape used in the patients router |
| Unauthorized/invalid auth | `test_authentication.py` | Malformed tokens, and tokens with no `clinic_id` claim (e.g. pre-onboarding), are both rejected |
| Role escalation / RBAC | `test_authorization_rbac.py` | `front_desk` role blocked from staff invite/billing actions; last-owner-removal safety check |
| Webhook forgery | `test_webhook_signatures.py` | Missing signature, tampered body, and wrong secret are all rejected; correctly-signed requests are accepted |
| Sensitive logging | `test_logging_redaction.py` | Static scan for the exact risky logging pattern found and fixed this pass, plus a unit test confirming `redact_exception()` never returns the exception's raw string form |
| AI safety | `test_ai_safety.py` | Messenger/Instagram get the PHI-restriction system prompt addition; other channels don't; unknown tool names return a safe error instead of crashing |

## What's explicitly NOT covered yet (honest gaps)

- **SQL injection**: not separately tested, because the codebase uses
  SQLAlchemy's parameterized query builder throughout (confirmed by
  code review in `ARCHITECTURE_SECURITY_AUDIT.md`) rather than string
  concatenation — the class of vulnerability these tests would catch
  doesn't have an obvious entry point to test against. Worth a
  dedicated pass if any raw SQL is ever added (the codebase does use
  `text()` in a few places — `app/api/v1/team.py`'s email lookup,
  `sql/*.sql` — those use bound parameters correctly, but any *new* raw
  SQL should be reviewed against this same standard).
- **XSS**: the frontend is React/Next.js, which escapes rendered content
  by default — no `dangerouslySetInnerHTML` usage found in this
  codebase. Not independently tested with an actual payload.
- **CSRF**: the API is token-based (Bearer JWT), not cookie-session-based,
  which structurally avoids most CSRF risk — not independently tested.
- **RLS enforcement itself**: `tests/security/` runs against SQLite,
  which doesn't have Postgres's RLS feature at all — these tests verify
  the *application-level* query-scoping logic, not that Postgres RLS
  policies actually block a bypass. That can only be tested against a
  real Postgres instance connected as the restricted `auradesk_app`
  role. **Recommended before production**: a manual (or CI-integrated,
  if you stand up a test Postgres instance) test that connects as
  `auradesk_app`, sets clinic A's claim, and attempts to `SELECT` a
  clinic B row directly — confirming zero rows return.
- **Rate limiting**: the sliding-window logic itself was verified this
  pass (exact limit enforcement, window expiry), but not tested against
  the live middleware/ASGI stack end-to-end.
- **File upload vulnerabilities**: N/A — this application doesn't accept
  file uploads anywhere in its current feature set.
- **Token leakage / secret exposure**: covered by the architecture audit
  (grep for hardcoded secrets, `NEXT_PUBLIC_` review), not by an
  automated test — worth adding a CI check that fails the build if a
  secret-shaped string appears in a git diff.
