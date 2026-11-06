import struct

def pcm_to_float(pcm_data: bytes):
    """Convert 16-bit PCM to float [-1.0, 1.0]"""
    samples = struct.unpack(f"{len(pcm_data)//2}h", pcm_data)
    return [s / 32768.0 for s in samples]

def float_to_pcm(float_samples):
    """Convert float [-1.0, 1.0] to 16-bit PCM"""
    pcm_samples = [int(s * 32767.0) for s in float_samples]
    return struct.pack(f"{len(pcm_samples)}h", *pcm_samples)


# --- Telephony / provider helpers (pure Python; audioop was removed in 3.13) ---
import array  # noqa: E402

_BIAS, _CLIP = 0x84, 32635


def _ulaw_decode_byte(u: int) -> int:
    u = ~u & 0xFF
    t = ((u & 0x0F) << 3) + _BIAS
    t <<= (u & 0x70) >> 4
    return (_BIAS - t) if u & 0x80 else (t - _BIAS)


_ULAW_TO_LIN = [_ulaw_decode_byte(i) for i in range(256)]


def _ulaw_encode_sample(s: int) -> int:
    sign = 0x80 if s < 0 else 0
    s = min(abs(s), _CLIP) + _BIAS
    exp, mask = 7, 0x4000
    while exp > 0 and not s & mask:
        exp, mask = exp - 1, mask >> 1
    return ~(sign | (exp << 4) | ((s >> (exp + 3)) & 0x0F)) & 0xFF


_LIN_TO_ULAW = bytes(_ulaw_encode_sample(i - 32768) for i in range(65536))


def ulaw_to_pcm16(data: bytes) -> bytes:
    return array.array("h", (_ULAW_TO_LIN[b] for b in data)).tobytes()


def pcm16_to_ulaw(pcm: bytes) -> bytes:
    return bytes(_LIN_TO_ULAW[s + 32768] for s in array.array("h", pcm))


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Linear-interpolation resampler for mono 16-bit PCM.

    shortcut: no anti-alias filter; fine for speech going to 8 kHz phone lines, swap for soxr if quality matters.
    """
    if src_rate == dst_rate or not pcm:
        return pcm
    src = array.array("h", pcm)
    n_out = len(src) * dst_rate // src_rate
    step, last = src_rate / dst_rate, len(src) - 1
    out = array.array("h", bytes(2 * n_out))
    for i in range(n_out):
        pos = i * step
        j = int(pos)
        frac = pos - j
        a = src[j]
        b = src[j + 1] if j < last else a
        out[i] = int(a + (b - a) * frac)
    return out.tobytes()
