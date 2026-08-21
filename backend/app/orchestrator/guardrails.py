"""
Lightweight guardrails for the AI Employee.

This is intentionally simple for Phase 2 — a keyword-level pre-classifier
for messages that should never get an AI-generated answer, plus a
post-response filter that strips anything that looks like a leaked
system prompt. Both are cheap, deterministic, and run before/after the
expensive model call. A model-based safety classifier is a reasonable
upgrade once real conversation volume exists to tune it against.
"""
import re

# Anything matching these patterns skips the AI entirely and goes straight
# to create_escalation — not phrased as clinical advice, just routing.
_URGENT_PATTERNS = [
    r"\ballerg(y|ic) reaction\b",
    r"\bcan'?t breathe\b",
    r"\bsevere pain\b",
    r"\bemergency\b",
    r"\bbleeding\b",
    r"\bfaint(ed|ing)?\b",
    r"\blawsuit\b",
    r"\blawyer\b",
    r"\bsue\b",
    r"\btalk to a (human|person|manager|someone)\b",
    r"\breal person\b",
]
_URGENT_RE = re.compile("|".join(_URGENT_PATTERNS), re.IGNORECASE)

# Phrases that, if they showed up in the AI's own reply, suggest a leaked
# system prompt or instruction rather than a normal answer.
_LEAK_PATTERNS = [
    r"as an ai (language )?model",
    r"my (system )?prompt",
    r"i (was|am) instructed to",
    r"you are (a|an) (ai|assistant)",
]
_LEAK_RE = re.compile("|".join(_LEAK_PATTERNS), re.IGNORECASE)


def needs_immediate_escalation(user_message: str) -> str | None:
    """Returns an escalation reason string if the message should bypass the AI, else None."""
    match = _URGENT_RE.search(user_message)
    if match:
        return f"Message matched urgent-escalation pattern: '{match.group(0)}'"
    return None


def strip_prompt_leaks(ai_text: str) -> str:
    if _LEAK_RE.search(ai_text):
        return "Let me get someone from our team to help with that."
    return ai_text
