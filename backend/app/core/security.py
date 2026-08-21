"""
Verifies Supabase-issued JWTs and extracts the claims our app and our
Postgres RLS policies both rely on: sub (user id), clinic_id, role.

Supabase projects now default to ES256 (asymmetric) signing, verified
against the project's published JWKS (see app/core/jwks.py). Older
projects — or ones that haven't migrated off the legacy secret — still
sign with HS256 against a static shared secret. We read the token's own
header to pick the right path rather than assuming one.

clinic_id and role are custom claims — Supabase Auth doesn't add them by
default. They're populated via the Custom Access Token Auth Hook
(sql/rls_policies.sql::custom_access_token_hook) at token-issue time.
"""
from dataclasses import dataclass

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core import jwks
from app.core.config import settings


@dataclass(frozen=True)
class AuthClaims:
    user_id: str
    clinic_id: str
    role: str
    email: str | None = None


def _decode_payload(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed session token"
        ) from exc

    alg = header.get("alg", "HS256")

    try:
        if alg == "HS256":
            return jwt.decode(
                token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated"
            )

        # ES256 (and any other asymmetric alg Supabase adopts) — verify against JWKS.
        kid = header.get("kid")
        key = jwks.get_jwk_for_kid(kid) if kid else None
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No matching signing key found for this token. It may have been issued "
                "by a different Supabase project, or the signing key just rotated — try logging "
                "in again.",
            )
        return jwt.decode(token, key, algorithms=[alg], audience="authenticated")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token"
        ) from exc


def decode_raw_claims(token: str) -> dict:
    """Verified payload, no clinic_id requirement — used by onboarding."""
    return _decode_payload(token)


def decode_supabase_jwt(token: str) -> AuthClaims:
    payload = _decode_payload(token)

    clinic_id = payload.get("clinic_id") or payload.get("app_metadata", {}).get("clinic_id")
    role = payload.get("role") or payload.get("app_metadata", {}).get("staff_role", "front_desk")
    user_id = payload.get("sub")

    if not user_id or not clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is missing required clinic context. Contact your administrator.",
        )

    return AuthClaims(user_id=user_id, clinic_id=clinic_id, role=role, email=payload.get("email"))
