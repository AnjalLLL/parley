# Voxwire

[![CI](https://github.com/AnjalLLL/voxwire/actions/workflows/ci.yml/badge.svg)](https://github.com/AnjalLLL/voxwire/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/voxwire)](https://pypi.org/project/voxwire/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Open-source, self-hostable real-time voice AI calls over WebRTC. A browser joins a call, and Voxwire streams its audio through a Pion SFU to the Gemini Live API and back.

You can use it in three ways:

| You want to… | Use |
|---|---|
| Run the whole stack yourself | Docker images: [`deploy/docker-compose.yml`](deploy/docker-compose.yml) |
| Create calls from your own backend | `pip install voxwire`, then `VoxwireClient` |
| Hack on or embed the server | `pip install "voxwire[server]"`, then `voxwire serve` |

## Architecture

```
Browser ──WebRTC/Opus──▶ SFU (Go, Pion) ──gRPC PCM 16k──▶ Server (Python) ──▶ Gemini Live
   ▲                         │                                 │
   └──── WebSocket signaling ┴─────────────────────────────────┘
```

| Directory | What it is | Published as |
|---|---|---|
| [`python/`](python) | Signaling server, audio pipeline, Python client + CLI | PyPI `voxwire`, image `ghcr.io/anjallll/voxwire-server` |
| [`sfu/`](sfu) | Pion SFU: WebRTC peers, Opus decode/encode, resampling | image `ghcr.io/anjallll/voxwire-sfu` |
| [`web/`](web) | Static landing page and browser call demo | static site |
| [`deploy/`](deploy) | Production compose file using the published images | n/a |

## Quickstart (self-host)

```bash
curl -O https://raw.githubusercontent.com/AnjalLLL/voxwire/main/deploy/docker-compose.yml
cat > .env <<ENV
GEMINI_API_KEY=your-key        # leave empty for echo mode
PION_PUBLIC_IP=203.0.113.10    # your server's public IP
ENV
docker compose up -d
```

## Use from your app

```python
from voxwire import VoxwireClient

vx = VoxwireClient("https://voice.example.com")
session = vx.create_session(system_prompt="You are a friendly support agent.")
# Give session["signaling_url"] to the browser; it sends its WebRTC offer there.
```

The signaling protocol is JSON over WebSocket: `{"type": "offer", "sdp": ...}`, `{"type": "ice-candidate", "candidate": ...}`, and the server replies `{"type": "answer", "sdp": ...}`. See [`web/index.html`](web/index.html) for a working browser client.

## Develop from source

Prerequisites: Docker, and for running outside Docker, Python 3.12+ with [uv](https://docs.astral.sh/uv/) and Go 1.24+ with libopus.

```bash
cp .env.example .env
docker compose up --build      # web :3000, server :8000, sfu gRPC :50051
```

Run the tests:

```bash
cd python && uv sync --extra server && uv run pytest
cd sfu && go test ./...
```

Regenerate the gRPC stubs after you edit `sfu/grpc/proto/sfu.proto`:

```bash
cd python && uv run python -m grpc_tools.protoc -I../sfu/grpc/proto \
  --python_out=src/voxwire/proto --grpc_python_out=src/voxwire/proto ../sfu/grpc/proto/sfu.proto
# then change `import sfu_pb2` to `from . import sfu_pb2` in sfu_pb2_grpc.py
```

Check Gemini connectivity with `cd python && uv run python ../scripts/test_gemini.py`.

## Audio pipeline

- Browser (Opus/RTP) → SFU (PCM 48 kHz) → resample to 16 kHz → server → Gemini
- Gemini (PCM 24 kHz) → server → SFU → resample to 48 kHz → Opus/RTP → browser

If you leave `GEMINI_API_KEY` empty, the server runs in echo mode and plays your own voice back to you, which helps you test without an API key.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), and follow our [Code of Conduct](CODE_OF_CONDUCT.md). To report a security issue, see [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE)
