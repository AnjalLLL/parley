import struct

def pcm_to_float(pcm_data: bytes):
    """Convert 16-bit PCM to float [-1.0, 1.0]"""
    samples = struct.unpack(f"{len(pcm_data)//2}h", pcm_data)
    return [s / 32768.0 for s in samples]

def float_to_pcm(float_samples):
    """Convert float [-1.0, 1.0] to 16-bit PCM"""
    pcm_samples = [int(s * 32767.0) for s in float_samples]
    return struct.pack(f"{len(pcm_samples)}h", *pcm_samples)
