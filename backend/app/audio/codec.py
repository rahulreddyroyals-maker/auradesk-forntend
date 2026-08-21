"""
Pure-Python G.711 mu-law codec, WAV wrapping, and naive linear resampling.

Python's stdlib `audioop` module (which used to do this) was removed in
Python 3.13 — this reimplements the standard ITU-T G.711 mu-law
algorithm directly rather than depending on a module that no longer
exists. Twilio Media Streams send/expect 8kHz mono mu-law audio; Groq
Whisper wants a WAV file; Cartesia's REST endpoint returns linear PCM at
whatever sample rate we request — this module is the glue between those
three formats.
"""
import io
import struct

_BIAS = 0x84
_CLIP = 32635

# Standard mu-law decode table (256 entries), generated once at import
# time from the algorithm rather than hand-copied, so it's verifiably
# correct against the spec rather than a pasted magic table.
def _build_decode_table() -> list[int]:
    table = []
    for u_val in range(256):
        u = ~u_val & 0xFF
        sign = u & 0x80
        exponent = (u >> 4) & 0x07
        mantissa = u & 0x0F
        sample = ((mantissa << 3) + _BIAS) << exponent
        sample -= _BIAS
        table.append(-sample if sign else sample)
    return table


_MULAW_DECODE_TABLE = _build_decode_table()


def mulaw_to_pcm16(data: bytes) -> bytes:
    """Decode 8-bit mu-law bytes to 16-bit signed little-endian PCM."""
    samples = [_MULAW_DECODE_TABLE[b] for b in data]
    return struct.pack(f"<{len(samples)}h", *samples)


def _linear_to_mulaw_sample(sample: int) -> int:
    sign = 0x00
    if sample < 0:
        sample = -sample
        sign = 0x80
    sample = min(sample, _CLIP) + _BIAS

    exponent = 7
    mask = 0x4000
    while exponent > 0 and not (sample & mask):
        exponent -= 1
        mask >>= 1

    mantissa = (sample >> (exponent + 3)) & 0x0F
    u_val = ~(sign | (exponent << 4) | mantissa) & 0xFF
    return u_val


def pcm16_to_mulaw(data: bytes) -> bytes:
    """Encode 16-bit signed little-endian PCM to 8-bit mu-law bytes."""
    count = len(data) // 2
    samples = struct.unpack(f"<{count}h", data[: count * 2])
    return bytes(_linear_to_mulaw_sample(s) for s in samples)


def wrap_pcm16_as_wav(pcm_bytes: bytes, sample_rate: int, channels: int = 1) -> bytes:
    """Wraps raw 16-bit PCM samples in a minimal WAV container."""
    byte_rate = sample_rate * channels * 2
    block_align = channels * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(pcm_bytes),
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        channels,
        sample_rate,
        byte_rate,
        block_align,
        16,  # bits per sample
        b"data",
        len(pcm_bytes),
    )
    return header + pcm_bytes


def resample_pcm16(pcm_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    """
    Naive linear-interpolation resampler. Good enough for phone-quality
    voice audio; a proper polyphase/sinc resampler would sound cleaner
    but isn't necessary at 8kHz telephony quality, where the codec itself
    is already the dominant source of quality loss.
    """
    if from_rate == to_rate:
        return pcm_bytes

    count = len(pcm_bytes) // 2
    if count == 0:
        return b""
    samples = struct.unpack(f"<{count}h", pcm_bytes)

    ratio = from_rate / to_rate
    out_count = int(count / ratio)
    out_samples = []
    for i in range(out_count):
        src_pos = i * ratio
        idx = int(src_pos)
        frac = src_pos - idx
        if idx + 1 < count:
            val = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        else:
            val = samples[idx]
        out_samples.append(max(-32768, min(32767, int(val))))

    return struct.pack(f"<{len(out_samples)}h", *out_samples)
