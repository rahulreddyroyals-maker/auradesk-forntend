"""Unauthenticated and malformed-token access must always be rejected."""
import pytest
from fastapi import HTTPException

from app.core.security import decode_supabase_jwt


def test_malformed_token_is_rejected():
    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt("not-a-real-jwt")
    assert exc_info.value.status_code == 401


def test_token_with_no_clinic_id_is_rejected():
    """A structurally valid but clinic-less token (e.g. right after signup, before onboarding) must not be treated as authorized for any clinic-scoped resource."""
    import jose.jwt as jose_jwt
    from app.core.config import settings

    token = jose_jwt.encode({"sub": "user-123", "aud": "authenticated"}, settings.SUPABASE_JWT_SECRET, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        decode_supabase_jwt(token)
    assert exc_info.value.status_code == 403


def test_valid_token_with_clinic_id_is_accepted():
    import jose.jwt as jose_jwt
    from app.core.config import settings

    token = jose_jwt.encode(
        {"sub": "user-123", "clinic_id": "clinic-abc", "role": "owner", "aud": "authenticated"},
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )
    claims = decode_supabase_jwt(token)
    assert claims.clinic_id == "clinic-abc"
    assert claims.role == "owner"
