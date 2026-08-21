# Environment Variables

Every variable actually read by the codebase (`app/core/config.py` on
the backend, `NEXT_PUBLIC_*` on the frontend) — nothing speculative.

## Backend (Railway) — set these in Railway's environment variable UI, never in Git

| Variable | Secret? | Required | Notes |
|---|---|---|---|
| `ENVIRONMENT` | No | Yes | Set to `production`. Disables `/docs`, shows the dev banner only when *not* production. |
| `DEBUG` | No | No | Leave unset/false in production. |
| `DATABASE_URL` | **Yes** | Yes | Restricted `auradesk_app` role connection string, once you've run `sql/restrict_app_role.sql` (see `/docs/security/`). Use Supabase's **pooler** connection string, not the direct one — Railway will make many concurrent connections. |
| `DATABASE_URL_ADMIN` | **Yes — more sensitive than DATABASE_URL** | Recommended | The `postgres` role connection string. Bypasses RLS. Falls back to `DATABASE_URL` if unset (not recommended for production — see security docs). |
| `SUPABASE_URL` | No (it's a public project ref) | Yes | |
| `SUPABASE_ANON_KEY` | No (designed to be public) | Yes | Used server-side here, but this specific key is safe in frontend code too — just not currently used there. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes — full database bypass** | Yes | Used for the Supabase Admin invite API (`app/integrations/supabase_admin.py`). Never expose this anywhere frontend-reachable. |
| `SUPABASE_JWT_SECRET` | **Yes** | Yes, unless project uses only ES256 | Legacy HS256 fallback — see `app/core/security.py`. |
| `TWILIO_ACCOUNT_SID` | No (identifier, not a secret) | Yes | |
| `TWILIO_AUTH_TOKEN` | **Yes** | Yes | |
| `TWILIO_PHONE_NUMBER` | No | Yes | Must match a `clinics.phone_number` value exactly. |
| `TWILIO_VALIDATE_SIGNATURE` | No | Yes | **Set to `true` in production** — it defaults `false` for local dev over ngrok. See `app/api/v1/sms.py` for what correct validation requires behind Railway's proxy. |
| `GROQ_API_KEY` | **Yes** | Yes | Backend-only, never sent to frontend — confirmed, no `NEXT_PUBLIC_GROQ*` variable exists anywhere in the codebase. |
| `CARTESIA_API_KEY` | **Yes** | Yes | |
| `ELEVENLABS_API_KEY` | **Yes** | Yes | |
| `META_APP_SECRET` | **Yes** | Yes | Used for webhook signature verification — required in production (signature check is skipped if unset, which is a dev convenience, not a production posture). |
| `META_PAGE_ACCESS_TOKEN` | **Yes** | No | Per-clinic tokens are actually stored in the `integrations` table via the Integrations page, not this global setting — this env var exists but isn't the primary path used. |
| `META_VERIFY_TOKEN` | **Yes** (shared secret with Meta) | Yes | |
| `STRIPE_SECRET_KEY` | **Yes** | Yes, once billing is live | |
| `STRIPE_WEBHOOK_SECRET` | **Yes** | Yes, once billing is live | |
| `SENTRY_DSN` | No (DSNs are meant to be embeddable) | No | Code path exists (`app/main.py`) but untested — no DSN has been configured/verified in this pass. |
| `POSTHOG_API_KEY` | No | No | **Not integrated** — this setting exists in config but nothing in the codebase uses it. Don't set it expecting analytics to start flowing. |
| `FRONTEND_ORIGINS` | No | Yes | JSON array, e.g. `["https://app.auradesk.com"]`. **Never `["*"]` in production** — confirmed the codebase never defaults to this. |

## Frontend (Vercel)

| Variable | Secret? | Required | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | No | Yes | |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | No | Yes | Designed to be public — Supabase's RLS is what actually protects data, not secrecy of this key. |
| `NEXT_PUBLIC_API_BASE_URL` | No | Yes | e.g. `https://api.auradesk.com/api/v1`. |

**No backend secret is ever referenced with a `NEXT_PUBLIC_` prefix
anywhere in the frontend codebase** — confirmed by grep across
`/frontend` as part of this pass. This is the one rule Next.js can't
enforce for you (any `NEXT_PUBLIC_*` variable ships to the browser
bundle regardless of intent), so it's worth re-checking manually any
time a new env var is added.

## Vercel/Railway environment separation

Both platforms support separate variable sets per environment
(Production / Preview / Development on Vercel; per-environment variable
groups on Railway). Use different Supabase pooler connection strings,
different Stripe keys (test vs. live), and different `FRONTEND_ORIGINS`
for each — don't reuse production credentials in a preview deployment.
