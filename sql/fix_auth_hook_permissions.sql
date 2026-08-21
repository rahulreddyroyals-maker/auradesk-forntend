-- Fixes: "Error running hook URI: pg-functions://postgres/public/custom_access_token_hook"
--
-- Auth Hooks run as the supabase_auth_admin role, which has no access to
-- your tables or even the public schema by default. This grants exactly
-- what custom_access_token_hook needs — nothing more — following
-- Supabase's documented pattern for Custom Access Token hooks.

grant usage on schema public to supabase_auth_admin;

grant execute
  on function public.custom_access_token_hook
  to supabase_auth_admin;

revoke execute
  on function public.custom_access_token_hook
  from authenticated, anon, public;

-- supabase_auth_admin needs to read `staff` to look up clinic_id/role.
-- RLS is enabled on staff (from rls_policies.sql), so a dedicated policy
-- for this specific role is required — the normal tenant-isolation
-- policy doesn't apply to it, since this call has no clinic_id claim yet.
grant select on public.staff to supabase_auth_admin;

drop policy if exists "Allow auth admin to read staff" on public.staff;
create policy "Allow auth admin to read staff" on public.staff
  as permissive for select
  to supabase_auth_admin
  using (true);
