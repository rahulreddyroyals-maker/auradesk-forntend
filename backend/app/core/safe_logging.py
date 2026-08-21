"""
Structured logging with built-in redaction discipline.

The rule this file exists to enforce: **never log patient conversation
content, full transcripts, API keys, tokens, or other secrets** — log
IDs, event types, and safe metadata instead. This isn't a framework
choice, it's a safety boundary — see docs/security/AI_SAFETY.md.

Usage:
    log_event("ai_conversation_completed", tenant_id=clinic_id, conversation_id=conv_id, status="success")

NOT:
    print(f"AI replied: {reply_text}")  # reply_text could contain PHI

This currently prints structured, single-line output (no external
logging service is wired up yet — Sentry is referenced in the original
architecture doc but not yet integrated). Swapping the implementation
of log_event() for a real structured-logging library (structlog,
python-json-logger) or shipping to Sentry/a log aggregator later is a
drop-in change — call sites don't need to change, since they already
only pass safe, structured metadata.
"""
import json
from datetime import datetime, timezone


def log_event(event: str, **metadata) -> None:
    """
    Log a structured, safe event. `metadata` values must be IDs, enums,
    booleans, counts, or other non-sensitive scalars — never message
    content, tokens, or secrets. This function does not attempt to
    inspect values for PHI; that discipline is enforced by what callers
    choose to pass in, which is why every call site matters.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **metadata,
    }
    print(json.dumps(record, default=str))


def redact_exception(exc: Exception) -> str:
    """
    Safe-to-log representation of an exception: type name and a
    generic reason only. Deliberately does NOT include str(exc) —
    HTTP client exceptions can echo back request/response bodies
    (which may contain message content sent to a vendor) in their
    string representation, and that's exactly the kind of leak this
    module exists to prevent.
    """
    return type(exc).__name__
