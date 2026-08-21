"""
Cartesia text-to-speech via the REST /tts/bytes endpoint. We request
pcm_s16le at a Cartesia-supported rate and resample locally (see
app/audio/codec.py) rather than assuming Cartesia accepts an arbitrary
8kHz request directly — this is a more conservative assumption that
costs one resample step but avoids depending on an unconfirmed low-level
API detail.

This is per-turn batch synthesis (call it once with the full reply
text), not word-by-word streaming — a real, working implementation, with
Cartesia's WebSocket streaming API (lower latency, maintains prosody
across incrementally-arriving text) as a natural upgrade path once voice
is proven out end-to-end.
"""
import httpx

from app.core.config import settings

CARTESIA_TTS_URL = "https://api.cartesia.ai/tts/bytes"
CARTESIA_VERSION = "2025-04-16"
DEFAULT_MODEL = "sonic-2"
CARTESIA_SAMPLE_RATE = 44100  # a broadly-supported rate; we resample down ourselves


def synthesize_speech_pcm(text: str, voice_id: str | None = None) -> bytes:
    """Returns raw 16-bit PCM audio at CARTESIA_SAMPLE_RATE, mono."""
    resp = httpx.post(
        CARTESIA_TTS_URL,
        headers={
            "Cartesia-Version": CARTESIA_VERSION,
            "X-API-Key": settings.CARTESIA_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "model_id": DEFAULT_MODEL,
            "transcript": text,
            "voice": {"mode": "id", "id": voice_id or "694f9389-aac1-45b6-b726-9d9369183238"},
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": CARTESIA_SAMPLE_RATE,
            },
            "language": "en",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.content
