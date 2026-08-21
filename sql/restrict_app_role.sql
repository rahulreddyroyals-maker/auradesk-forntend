-- =====================================================================
-- AuraDesk — Restrict the backend's database role
-- =====================================================================
-- Run this in the Supabase SQL editor, AFTER rls_policies.sql.
--
-- WHY: Postgres automatically exempts table owners (and superusers) from
-- their own RLS policies. Since the backend has been connecting as the
-- `postgres` role — which owns every table it created via migrations —
-- RLS has been enforced in documentation only, not in practice. Every
-- correct clinic_id filter in application code has been the ONLY thing
-- preventing cross-tenant access. That's fine for development; it's not
-- what you want with 50 real businesses' patient data flowing through
-- one database.
--
-- This creates a new role that is NOT a table owner — Postgres applies
-- RLS to it automatically, no extra "FORCE ROW LEVEL SECURITY" needed.
-- After running this, set DATABASE_URL to connect as this role, and set
-- DATABASE_URL_ADMIN to your existing `postgres` connection string (kept
-- for migrations and the handful of bootstrapping operations — onboarding,
-- and each webhook's initial "which clinic does this belong to" lookup —
-- that structurally can't be RLS-scoped yet; see app/db/session.py's
-- module docstring for the full list and reasoning). Now a bug that
-- forgets a clinic_id filter fails closed (returns nothing / errors)
-- instead of leaking data, because the database itself won't return
-- other clinics' rows to the restricted role regardless of what the
-- application asks for.
--
-- This is opt-in, additive hardening — nothing breaks if you don't run
-- this. DATABASE_URL_ADMIN falls back to DATABASE_URL automatically
-- until you split them. Recommended before real client data flows
-- through, not required for continued local development.
-- =====================================================================

-- Pick a strong password yourself — this is a real credential.
create role auradesk_app with login password 'REPLACE_WITH_A_STRONG_PASSWORD';

grant usage on schema public to auradesk_app;

grant select, insert, update, delete on all tables in schema public to auradesk_app;

-- Ensures tables created by FUTURE migrations are automatically
-- accessible too, without needing to re-run grants after every
-- `alembic upgrade head`.
alter default privileges in schema public
  grant select, insert, update, delete on tables to auradesk_app;

-- This role must NOT be able to create/drop tables (that stays a
-- migration-time operation using the `postgres` role) — the grants
-- above are deliberately narrower than that.
