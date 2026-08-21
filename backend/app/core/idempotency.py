"""
Webhook idempotency guard. Twilio (and most webhook senders) retry
delivery on a non-2xx response or a timeout — without tracking which
deliveries we've already processed, a slow response (e.g. a Groq retry
taking a few extra seconds) could cause the same SMS/call to be
processed twice, sending the patient a duplicate reply.

Same scaling caveat as app/core/rate_limit.py: in-memory, single-process
only. Multiple backend instances would each track their own seen-set,
which doesn't prevent duplicates across instances. Move to a shared
store (Redis, or a dedicated table with a unique constraint on the
vendor's delivery ID) before scaling past one instance.
"""
import time

_TTL_SECONDS = 300  # 5 minutes comfortably covers any realistic retry window
_seen: dict[str, float] = {}


def already_processed(key: str) -> bool:
    """Returns True if this key was seen recently. Marks it seen either way."""
    now = time.monotonic()
    # Opportunistic cleanup of expired entries — avoids unbounded growth
    # without needing a separate background sweep.
    expired = [k for k, ts in _seen.items() if now - ts > _TTL_SECONDS]
    for k in expired:
        del _seen[k]

    if key in _seen:
        return True
    _seen[key] = now
    return False
