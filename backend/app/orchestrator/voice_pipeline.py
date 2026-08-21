"""
One CallSession per active phone call. Twilio sends audio in ~20ms mulaw
frames (160 bytes each at 8kHz) over the Media Streams WebSocket; this
buffers them, detects when the caller has stopped talking (simple
energy-based silence detection — good enough for phone-quality audio,
not a full VAD model), and on end-of-utterance runs the STT -> orchestrator
-> TTS pipeline and streams the reply back as more mulaw frames.
"""
import base64
import json
import struct
import time
from datetime import datetime, timezone

from starlette.concurrency import run_in_threadpool

from app.audio.codec import mulaw_to_pcm16, pcm16_to_mulaw, resample_pcm16, wrap_pcm16_as_wav
from app.core.safe_logging import log_event, redact_exception
from app.db.session import SessionLocal, bind_clinic_context
from app.integrations import cartesia_client, elevenlabs_client
from app.integrations.groq_client import transcribe_audio
from app.models import Call, ChannelType, Conversation, ConversationStatus
from app.orchestrator.session import handle_message

FRAME_MS = 20
SAMPLE_RATE = 8000
SILENCE_AMPLITUDE_THRESHOLD = 300  # mean abs PCM16 amplitude below this counts as silence
MIN_SPEECH_FRAMES = 10  # ~200ms — avoids triggering on a single noise blip
SILENCE_END_FRAMES = 35  # ~700ms of quiet after speech = they're done talking
MAX_UTTERANCE_SECONDS = 20  # force-process even without silence, so a long ramble doesn't hang forever

TWILIO_OUTBOUND_CHUNK_MS = 20
TWILIO_OUTBOUND_CHUNK_BYTES = int(SAMPLE_RATE * TWILIO_OUTBOUND_CHUNK_MS / 1000)  # 160 bytes mulaw


def _frame_amplitude(mulaw_chunk: bytes) -> float:
    pcm = mulaw_to_pcm16(mulaw_chunk)
    if not pcm:
        return 0.0
    count = len(pcm) // 2
    samples = struct.unpack(f"<{count}h", pcm)
    return sum(abs(s) for s in samples) / count


def synthesize_with_fallback(text: str) -> tuple[bytes, int]:
    """Returns (pcm_bytes, sample_rate). Tries Cartesia first, falls back to ElevenLabs."""
    try:
        pcm = cartesia_client.synthesize_speech_pcm(text)
        return pcm, cartesia_client.CARTESIA_SAMPLE_RATE
    except Exception as exc:  # noqa: BLE001 — any Cartesia failure should fall back, not crash the call
        log_event("tts_provider_fallback", provider="cartesia", error_type=redact_exception(exc))
        pcm = elevenlabs_client.synthesize_speech_pcm(text)
        return pcm, elevenlabs_client.ELEVENLABS_SAMPLE_RATE


class CallSession:
    def __init__(self, clinic_id: str, call_sid: str, stream_sid: str):
        self.clinic_id = clinic_id
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.db = SessionLocal()
        bind_clinic_context(self.db, clinic_id)
        self.conversation_id: str | None = None

        self._buffer = bytearray()
        self._speaking_frames = 0
        self._silence_frames = 0
        self._utterance_started_at: float | None = None

    def start(self) -> None:
        conv = Conversation(
            clinic_id=self.clinic_id,
            channel=ChannelType.voice,
            status=ConversationStatus.active,
            started_at=datetime.now(timezone.utc),
            ai_handled=True,
        )
        self.db.add(conv)
        self.db.flush()
        self.db.add(
            Call(
                conversation_id=conv.id,
                twilio_call_sid=self.call_sid,
                direction="inbound",
                created_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()
        self.conversation_id = str(conv.id)

    def end(self) -> None:
        if self.conversation_id:
            conv = self.db.get(Conversation, self.conversation_id)
            if conv and conv.status == ConversationStatus.active:
                conv.ended_at = datetime.now(timezone.utc)
                conv.status = ConversationStatus.resolved
                self.db.commit()
        self.db.close()

    async def handle_frame(self, mulaw_chunk: bytes, send_audio) -> None:
        """send_audio: async callable(mulaw_bytes) -> None, sends audio back to Twilio."""
        amplitude = _frame_amplitude(mulaw_chunk)
        is_speech = amplitude > SILENCE_AMPLITUDE_THRESHOLD

        if is_speech:
            if self._utterance_started_at is None:
                self._utterance_started_at = time.monotonic()
            self._buffer.extend(mulaw_chunk)
            self._speaking_frames += 1
            self._silence_frames = 0
            return

        # Silent frame
        if self._speaking_frames >= MIN_SPEECH_FRAMES:
            self._buffer.extend(mulaw_chunk)  # keep a little trailing silence, sounds more natural for STT
            self._silence_frames += 1

        duration = time.monotonic() - self._utterance_started_at if self._utterance_started_at else 0
        should_process = self._speaking_frames >= MIN_SPEECH_FRAMES and (
            self._silence_frames >= SILENCE_END_FRAMES or duration >= MAX_UTTERANCE_SECONDS
        )
        if should_process:
            await self._process_utterance(send_audio)

    async def _process_utterance(self, send_audio) -> None:
        mulaw_bytes = bytes(self._buffer)
        self._buffer = bytearray()
        self._speaking_frames = 0
        self._silence_frames = 0
        self._utterance_started_at = None

        pcm = mulaw_to_pcm16(mulaw_bytes)
        wav = wrap_pcm16_as_wav(pcm, sample_rate=SAMPLE_RATE)

        transcript = await run_in_threadpool(transcribe_audio, wav)
        if not transcript:
            return  # nothing intelligible — just keep listening

        result = await run_in_threadpool(
            handle_message,
            self.db,
            self.clinic_id,
            ChannelType.voice,
            transcript,
            self.conversation_id,
        )
        reply_text = result["reply"]

        reply_pcm, reply_rate = await run_in_threadpool(synthesize_with_fallback, reply_text)
        reply_pcm_8k = resample_pcm16(reply_pcm, reply_rate, SAMPLE_RATE)
        reply_mulaw = pcm16_to_mulaw(reply_pcm_8k)

        for i in range(0, len(reply_mulaw), TWILIO_OUTBOUND_CHUNK_BYTES):
            chunk = reply_mulaw[i : i + TWILIO_OUTBOUND_CHUNK_BYTES]
            await send_audio(chunk)
