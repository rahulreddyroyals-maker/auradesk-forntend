"""
Basic rate limiting for the public, unauthenticated webhook endpoints
(Twilio, Meta). Signature verification confirms the *sender* is
legitimate; it does nothing to limit *volume* — without this, a bad
actor (or a misbehaving retry loop on the vendor's side) could drive up
Groq/Twilio/Cartesia usage costs by hammering these endpoints.

This is an in-memory, single-process sliding window — correct for one
backend instance, NOT correct if you horizontally scale to multiple
backend processes/containers (each would track its own counts,
effectively multiplying the real limit by the instance count). Replace
with a Redis-backed limiter (e.g. slowapi with a Redis backend) before
scaling past one instance.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

RATE_LIMITED_PREFIXES = ("/api/v1/sms/webhook", "/api/v1/calls/incoming", "/api/v1/messenger/webhook", "/api/v1/instagram/webhook")
WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 30  # generous for legitimate traffic; tune once real volume is observed

_request_log: dict[str, deque] = defaultdict(deque)


class WebhookRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not any(request.url.path.startswith(p) for p in RATE_LIMITED_PREFIXES):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        log = _request_log[client_ip]

        while log and now - log[0] > WINDOW_SECONDS:
            log.popleft()

        if len(log) >= MAX_REQUESTS_PER_WINDOW:
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again shortly."})

        log.append(now)
        return await call_next(request)
