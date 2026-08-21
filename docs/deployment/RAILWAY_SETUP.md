# Railway Setup

## 1. Create the service

1. New Project → Deploy from GitHub repo.
2. **Root Directory**: set to `backend`.
3. Railway will detect the `Dockerfile` and `railway.json` in that
   directory automatically. (If you'd rather skip Docker and use
   Railway's Nixpacks auto-builder instead, delete/rename
   `railway.json`'s `builder: DOCKERFILE` line — either path works,
   Docker was built this pass because the task asked for one and it
   guarantees the deployed environment matches exactly what was tested
   locally.)

## 2. Environment variables

Add every backend variable from `ENVIRONMENT_VARIABLES.md`. Set
`ENVIRONMENT=production` and `TWILIO_VALIDATE_SIGNATURE=true` — both
default to dev-safe values that are wrong for production if left unset.

## 3. Health check

Already configured in `railway.json`: `GET /health`, 30s timeout,
restart on failure (max 5 retries). Nothing further to configure.

## 4. Migrations

Run once, manually, before the first real traffic — not automatically
on every deploy (a migration that fails mid-deploy shouldn't take the
whole service down):

```bash
railway run --service <your-backend-service> python -m alembic upgrade head
```

This uses `DATABASE_URL_ADMIN` internally (`app/db/migrations/env.py`)
since the restricted runtime role has no DDL rights — confirm that
variable is set before running this.

## 5. The follow-up worker

Add a second, separate Railway **Cron Job** (not a service) in the same
project, same repo/root directory, with the command:

```bash
python -m app.workers.followup_scheduler
```

on whatever schedule you want (e.g. every 30 minutes). This replaces
the Windows Task Scheduler approach used for local dev.

## 6. Custom domain

Settings → Networking → Custom Domain → `api.auradesk.com`. Railway
shows the CNAME to add — see `DNS_SETUP.md`.

## 7. Before going live — verified this pass

- App binds `0.0.0.0:$PORT`, not a hardcoded port — confirmed in
  `Procfile`/`Dockerfile`.
- `--reload` is never used in the production command — confirmed.
- `/docs` (Swagger UI) is disabled when `ENVIRONMENT != development` —
  confirmed, was already true before this pass.
- Security headers added on every response.
- Groq calls retry on transient failures (timeout/5xx/429) and fail
  safe (escalate to a human) if retries exhaust — added and tested this
  pass.
- SMS webhook is idempotent against Twilio's retry-on-failure behavior
  — added this pass.
- Rate limiting on public webhook endpoints — added in the previous
  security pass.

## 8. What you still need to do

- Actually create the Railway project (I don't have access to create
  this on your behalf).
- Set all environment variables with real production credentials.
- Run the migration once, manually, before real traffic.
- Set up the Cron Job for the follow-up worker.
- Point Twilio/Meta/Stripe webhook URLs at the real `api.auradesk.com`
  address once DNS is live (see `DNS_SETUP.md`) — they can't be
  configured against `localhost` or a placeholder URL.
- Verify the WebSocket endpoint (`/calls/media-stream`) actually works
  through Railway's routing — untested against live Railway
  infrastructure in this pass.
