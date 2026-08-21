-- =====================================================================
-- AuraDesk — Row Level Security Policies
-- =====================================================================
-- Run this AFTER the Alembic migration creates the tables.
--
-- Strategy: every tenant-scoped table gets RLS enabled + a single policy
-- that compares the row's clinic_id to a Postgres session-local setting,
-- `request.jwt.claim.clinic_id`. That setting is populated two ways:
--   1. By our FastAPI backend, via set_config() in db/session.py::set_rls_claims,
--      using the clinic_id it already verified from the Supabase JWT.
--   2. By Supabase's PostgREST layer directly (if any table is ever queried
--      straight from the frontend via supabase-js) using the same JWT claim,
--      via the Auth Hook below that stamps clinic_id onto every token.
--
-- This means tenant isolation holds even if application code has a bug —
-- Postgres itself refuses the cross-tenant row.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Auth Hook: stamp clinic_id + role onto every issued JWT.
--    Configure this as a "Custom Access Token" Auth Hook in the Supabase
--    dashboard (Authentication > Hooks), pointing at this function.
-- ---------------------------------------------------------------------
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
as $$
declare
  claims jsonb;
  staff_row record;
begin
  select clinic_id, role into staff_row
  from public.staff
  where user_id = (event ->> 'user_id')::uuid
  limit 1;

  claims := event -> 'claims';

  if staff_row.clinic_id is not null then
    claims := jsonb_set(claims, '{clinic_id}', to_jsonb(staff_row.clinic_id::text));
    claims := jsonb_set(claims, '{role}', to_jsonb(staff_row.role::text));
  end if;

  event := jsonb_set(event, '{claims}', claims);
  return event;
end;
$$;

-- ---------------------------------------------------------------------
-- 2. Helper: read the current request's clinic_id, from whichever path
--    set it (FastAPI's set_config, or PostgREST's native JWT parsing).
-- ---------------------------------------------------------------------
create or replace function public.current_clinic_id()
returns uuid
language sql
stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claim.clinic_id', true), ''),
    (current_setting('request.jwt.claims', true)::jsonb ->> 'clinic_id')
  )::uuid;
$$;

-- ---------------------------------------------------------------------
-- 3. Enable RLS + policy per tenant-scoped table.
--    Template: USING (clinic_id = current_clinic_id())
--    Service-role connections (used by background workers) bypass RLS
--    entirely per Supabase convention — only the authenticated role is
--    restricted here.
-- ---------------------------------------------------------------------
do $$
declare
  t text;
  tenant_tables text[] := array[
    'clinics',              -- special-cased below (id, not clinic_id)
    'staff', 'ai_employees', 'patients', 'conversations',
    'services', 'memberships', 'calendar_connections', 'appointments',
    'knowledge_base_articles', 'escalations', 'integrations', 'usage_events'
  ];
begin
  foreach t in array tenant_tables loop
    execute format('alter table %I enable row level security', t);
  end loop;
end $$;

-- clinics: a staff member can only see their own clinic row (by id, not clinic_id)
create policy clinics_tenant_isolation on clinics
  for all
  using (id = public.current_clinic_id());

-- All other tenant tables follow the same clinic_id = current_clinic_id() shape.
create policy staff_tenant_isolation on staff for all using (clinic_id = public.current_clinic_id());
create policy ai_employees_tenant_isolation on ai_employees for all using (clinic_id = public.current_clinic_id());
create policy patients_tenant_isolation on patients for all using (clinic_id = public.current_clinic_id());
create policy conversations_tenant_isolation on conversations for all using (clinic_id = public.current_clinic_id());
create policy services_tenant_isolation on services for all using (clinic_id = public.current_clinic_id());
create policy memberships_tenant_isolation on memberships for all using (clinic_id = public.current_clinic_id());
create policy calendar_connections_tenant_isolation on calendar_connections for all using (clinic_id = public.current_clinic_id());
create policy appointments_tenant_isolation on appointments for all using (clinic_id = public.current_clinic_id());
create policy kb_articles_tenant_isolation on knowledge_base_articles for all using (clinic_id = public.current_clinic_id());
create policy escalations_tenant_isolation on escalations for all using (clinic_id = public.current_clinic_id());
create policy integrations_tenant_isolation on integrations for all using (clinic_id = public.current_clinic_id());
create policy usage_events_tenant_isolation on usage_events for all using (clinic_id = public.current_clinic_id());

-- ---------------------------------------------------------------------
-- 4. messages / calls: scoped indirectly via their parent conversation,
--    since they don't carry clinic_id directly (avoids a denormalized
--    column that could drift from the conversation's real tenant).
-- ---------------------------------------------------------------------
alter table messages enable row level security;
create policy messages_tenant_isolation on messages
  for all
  using (
    conversation_id in (
      select id from conversations where clinic_id = public.current_clinic_id()
    )
  );

alter table calls enable row level security;
create policy calls_tenant_isolation on calls
  for all
  using (
    conversation_id in (
      select id from conversations where clinic_id = public.current_clinic_id()
    )
  );

-- ---------------------------------------------------------------------
-- 5. Auth Hook permissions.
--    Auth Hooks execute as the `supabase_auth_admin` role, which has NO
--    access to the public schema or any table by default — not even
--    ones the hook itself needs to query. Without these grants, the
--    hook fails at login/refresh time with "Error running hook URI:
--    pg-functions://postgres/public/custom_access_token_hook" (visible
--    as a 500 on the token endpoint), even though the function itself
--    is syntactically correct.
-- ---------------------------------------------------------------------
grant usage on schema public to supabase_auth_admin;

grant execute
  on function public.custom_access_token_hook
  to supabase_auth_admin;

revoke execute
  on function public.custom_access_token_hook
  from authenticated, anon, public;

-- The hook needs to read `staff` to look up clinic_id/role. RLS is
-- enabled on staff above, so a dedicated policy for this specific role
-- is required — the tenant-isolation policy doesn't apply here, since
-- this call happens before any clinic_id claim exists.
grant select on public.staff to supabase_auth_admin;

create policy "Allow auth admin to read staff" on public.staff
  as permissive for select
  to supabase_auth_admin
  using (true);
