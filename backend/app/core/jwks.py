"""
Supabase projects created after the JWT Signing Keys rollout sign access
tokens with ES256 (asymmetric) by default, not the legacy HS256 shared
secret. Verification for ES256 tokens requires the project's public keys,
published at /auth/v1/.well-known/jwks.json. This module fetches and
caches that key set.

We still support HS256 as a fallback (older projects, or ones that
haven't migrated off the legacy secret) — see decode_supabase_jwt in
security.py, which picks the verification path based on the token's
own `alg` header.

Per Supabase's docs, the JWKS response is edge-cached for ~10 minutes,
so a matching local cache TTL avoids hammering the endpoint without
risking stale-key rejections after a rotation.
"""
import time

import httpx

from app.core.config import settings

_CACHE_TTL_SECONDS = 600
_cache: dict[str, object] = {"fetched_at": 0.0, "keys_by_kid": {}}


def _jwks_url() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"


def get_jwk_for_kid(kid: str) -> dict | None:
    now = time.time()
    if now - _cache["fetched_at"] > _CACHE_TTL_SECONDS or kid not in _cache["keys_by_kid"]:
        _refresh(now)
    return _cache["keys_by_kid"].get(kid)


def _refresh(now: float) -> None:
    resp = httpx.get(_jwks_url(), timeout=5.0)
    resp.raise_for_status()
    keys = resp.json().get("keys", [])
    _cache["keys_by_kid"] = {k["kid"]: k for k in keys if "kid" in k}
    _cache["fetched_at"] = now
