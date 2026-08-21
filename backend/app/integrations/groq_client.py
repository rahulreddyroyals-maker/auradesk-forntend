"""
Thin wrapper around Groq's OpenAI-compatible chat completions endpoint.

Groq's model lineup changes fairly often (they deprecated llama-3.3-70b-
versatile and llama-3.1-8b-instant in June 2026 in favor of the gpt-oss
family) — GROQ_MODEL is a plain setting, not hardcoded, so swapping
models doesn't require touching orchestration logic. Check
https://console.groq.com/docs/models before depending on a specific one.

Retry policy: transient failures (connection errors, timeouts, and 5xx/
429 responses) get a small number of retries with exponential backoff.
Anything else (4xx auth/validation errors) fails immediately — retrying
a bad request just wastes the budget and the caller's patience.
"""
import time

import httpx

from app.core.config import settings
from app.core.safe_logging import log_event, redact_exception

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
WHISPER_MODEL = "whisper-large-v3-turbo"

MAX_RETRIES = 2
BACKOFF_BASE_SECONDS = 1.0


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = httpx.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES and _is_retryable(exc):
                wait = BACKOFF_BASE_SECONDS * (2**attempt)
                log_event("groq_request_retry", attempt=attempt + 1, error_type=redact_exception(exc), wait_seconds=wait)
                time.sleep(wait)
                continue
            raise
    raise last_exc  # unreachable in practice, satisfies type checkers


def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
    temperature: float = 0.3,
    model: str | None = None,
) -> dict:
    """
    Returns the raw `choices[0].message` dict from Groq's response — may
    contain `content` (text), `tool_calls`, or both depending on what the
    model decided to do this turn.
    """
    payload: dict = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    resp = _request_with_retry(
        "POST",
        GROQ_CHAT_URL,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=30.0,
    )
    data = resp.json()
    return data["choices"][0]["message"]


def transcribe_audio(wav_bytes: bytes, language: str = "en") -> str:
    """
    Transcribes a WAV audio clip via Groq's Whisper Large v3 Turbo.
    Whisper wants at least ~30s of audio for best results; shorter clips
    (a typical single utterance) are automatically padded with silence
    by the API rather than rejected, so short turns are fine.
    """
    resp = _request_with_retry(
        "POST",
        GROQ_TRANSCRIPTION_URL,
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"model": WHISPER_MODEL, "language": language, "response_format": "json"},
        timeout=30.0,
    )
    return resp.json().get("text", "").strip()
