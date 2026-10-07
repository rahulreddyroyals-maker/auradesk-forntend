"""
Supabase Admin API calls that aren't available via plain SQL — inviting a
new user by email (sends Supabase's built-in invite email with a magic
link) uses GoTrue's admin endpoint, not a database operation.
"""
import httpx

from app.core.config import settings


def invite_user_by_email(email: str) -> str:
    """Returns the newly-created auth user's id."""
    resp = httpx.post(
        f"{settings.SUPABASE_URL}/auth/v1/invite",
        headers={
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        },
        json={"email": email},
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def find_user_id_by_email(email: str) -> str | None:
    """
    Paginates GoTrue's admin user list looking for an exact email match.
    Used instead of relying on a `?email=` filter query param, since
    support for that varies across GoTrue versions — listing and
    filtering client-side works on every version.
    """
    target = email.strip().lower()
    for page in range(1, 11):  # up to 2,000 users — comfortably covers a solo project
        resp = httpx.get(
            f"{settings.SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            },
            params={"page": page, "per_page": 200},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        users = data.get("users", data) if isinstance(data, dict) else data
        if not users:
            return None
        for u in users:
            if (u.get("email") or "").strip().lower() == target:
                return u["id"]
        if len(users) < 200:
            return None
    return None


def get_or_create_user_with_password(email: str, password: str) -> str:
    """
    Creates a Supabase Auth user with a known password and email already
    confirmed (so it can log in immediately, with no invite-email/magic-
    link step) — used only for the demo account, never for a real
    clinic's owner. If the user already exists, returns its existing id
    unchanged (this function never resets an existing user's password,
    so re-running the demo seed can't accidentally lock out whoever is
    mid-demo with the credentials already in hand).
    """
    resp = httpx.post(
        f"{settings.SUPABASE_URL}/auth/v1/admin/users",
        headers={
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        },
        json={"email": email, "password": password, "email_confirm": True},
        timeout=15.0,
    )
    if resp.status_code in (400, 422):
        # Most likely "already registered" — look up the existing id
        # rather than treating this as a failure.
        existing_id = find_user_id_by_email(email)
        if existing_id:
            return existing_id
        resp.raise_for_status()  # a genuinely different 400/422 — surface it
    resp.raise_for_status()
    return resp.json()["id"]
