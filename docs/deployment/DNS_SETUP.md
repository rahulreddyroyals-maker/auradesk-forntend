# DNS Setup

**These domains don't exist yet** — this documents what records to
create once you own `auradesk.com` (or whatever domain you're actually
using), not an assumption that they're already configured.

## Recommended structure

| Subdomain | Points to | Record type |
|---|---|---|
| `app.auradesk.com` | Vercel | CNAME → the value Vercel shows under Project Settings → Domains |
| `api.auradesk.com` | Railway | CNAME → the value Railway shows under Settings → Networking → Custom Domain |

## Why subdomains, not the bare root domain

Keeps frontend and backend cleanly separable — you can move either to a
different provider later without touching the other's DNS, and CORS
configuration (`FRONTEND_ORIGINS`) stays simple (one exact origin to
allow, not a wildcard).

## After DNS propagates

1. Update the backend's `FRONTEND_ORIGINS` to `["https://app.auradesk.com"]`.
2. Update the frontend's `NEXT_PUBLIC_API_BASE_URL` to
   `https://api.auradesk.com/api/v1`.
3. Redeploy both (env var changes require a redeploy on both platforms
   to take effect).
4. Only now configure Twilio/Meta/Stripe webhook URLs against
   `api.auradesk.com` — they need a stable, real HTTPS domain, not
   Railway's auto-generated `*.up.railway.app` URL (which works fine
   too, if you'd rather skip custom domains initially and just use
   Railway's default URL for the backend — the webhook config just
   needs to be updated again if you add a custom domain later).
