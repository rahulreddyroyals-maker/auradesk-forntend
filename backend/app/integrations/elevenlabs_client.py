"""
ElevenLabs TTS fallback, used only when Cartesia errors or times out (see
voice_pipeline.py). Requests raw PCM directly via output_format=pcm_16000
rather than the default MP3, so this pipeline never needs an MP3 decoder
dependency.
"""
import httpx

from app.core.config import settings

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — a standard premade ElevenLabs voice
ELEVENLABS_SAMPLE_RATE = 16000


def synthesize_speech_pcm(text: str, voice_id: str | None = None) -> bytes:
    """Returns raw 16-bit PCM audio at ELEVENLABS_SAMPLE_RATE, mono."""
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id or DEFAULT_VOICE_ID)
    resp = httpx.post(
        url,
        headers={"xi-api-key": settings.ELEVENLABS_API_KEY, "Content-Type": "application/json"},
        params={"output_format": f"pcm_{ELEVENLABS_SAMPLE_RATE}"},
        json={"text": text, "model_id": "eleven_turbo_v2_5"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.content
