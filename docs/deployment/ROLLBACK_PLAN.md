# Rollback Plan

## Frontend (Vercel)

Vercel keeps every previous deployment. Rollback: Project → Deployments
→ find the last known-good deployment → "Promote to Production." Takes
effect immediately, no rebuild needed. This is the fastest rollback
path in the whole stack.

## Backend (Railway)

Railway keeps deployment history per service. Rollback: Service →
Deployments → select a previous deployment → Redeploy. Takes a minute
or two (rebuilds/restarts the container).

## Database migrations

**The one rollback that isn't instant or safe by default.** Every
migration in this codebase has a `downgrade()` function (Alembic
convention, confirmed present in all migrations under
`app/db/migrations/versions/`), but running one against production data
is a real, potentially destructive operation — not a click-to-revert
button like the two above.

Before rolling back a migration against production:
1. Confirm what the `downgrade()` actually does (some, like dropping a
   column, are irreversible data loss — e.g. rolling back the
   `subscriptions` or `audit_logs` migrations would delete those
   tables' data entirely).
2. Take a manual Supabase backup/snapshot first if the migration
   touched anything with real data in it.
3. Run `python -m alembic downgrade -1` using `DATABASE_URL_ADMIN`,
   the same way migrations are applied.

**Never run a destructive migration rollback against production without
this explicit confirmation step** — per the deployment task's own
instruction, and because several of this app's migrations (patients'
`external_ids_json`, `subscriptions`, `audit_logs`) hold real data once
in production use.

## If a deploy breaks something and you need to act fast

1. Roll back the frontend first (fastest, buys time) if the issue is
   frontend-visible.
2. Roll back the backend deployment (not the database) next — this
   fixes the vast majority of "bad deploy" scenarios, since most
   changes are code, not schema.
3. Only touch the database migration if the broken deploy specifically
   added a migration that's causing the problem — and follow the
   confirmation steps above even then.
