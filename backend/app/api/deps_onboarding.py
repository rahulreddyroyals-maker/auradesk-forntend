"""
Onboarding needs a different auth shape than the rest of the app: a
freshly-signed-up Supabase user has no `staff` row yet, so the Auth Hook
has nothing to stamp `clinic_id`/`role` with — their JWT is valid but
"clinic-less". get_current_session (deps.py) rejects that on purpose, so
onboarding uses this narrower dependency instead: verify the token (same
ES256/JWKS-or-HS256 logic as everywhere else), but only require `sub`.
"""
from fastapi import Header, HTTPException, status

from app.core.security import decode_raw_claims


def get_authenticated_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_raw_claims(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
    return user_id
