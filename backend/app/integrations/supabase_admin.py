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
