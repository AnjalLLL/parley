# Parley

Open-source, self-hostable real-time voice AI calls. Parley provides a complete pipeline for AI-powered video/audio calls using FastAPI, Pion SFU, and the Gemini Live API.

## Architecture

- **FastAPI (Python):** Handles signaling (WebSockets), session management, and orchestration between the SFU and Gemini.
- **Pion SFU (Go):** Manages WebRTC peer connections, handles RTP media, and performs audio transcoding/resampling.
- **Gemini Live API:** Provides real-time AI conversation with native audio streaming.

## Prerequisites

- Python 3.11+
- Go 1.22+
- `uv` (Python package manager)
- Docker & Docker Compose
- Google Gemini API Key

## Setup

1. **Environment Variables:**
   Copy `.env.example` to `.env` and add your `GEMINI_API_KEY`.
   ```bash
   cp .env.example .env
   ```

2. **Python Dependencies:**
   ```bash
   cd fastapi_service
   uv sync
   ```

3. **Go Dependencies:**
   ```bash
   cd pion_service
   go mod tidy
   ```

4. **Generate gRPC Stubs:**
   ```bash
   # Python
   cd fastapi_service
   uv run python -m grpc_tools.protoc -I../pion_service/grpc/proto --python_out=./proto --grpc_python_out=./proto ../pion_service/grpc/proto/sfu.proto
   ```

## Running with Docker (Recommended)

Start the entire stack:
```bash
docker-compose up --build
```

- **Frontend:** http://localhost:3000
- **FastAPI:** http://localhost:8000
- **Pion gRPC:** localhost:50051

## Testing

1. **Gemini Connectivity:**
   ```bash
   cd fastapi_service
   uv run python ../scripts/test_gemini.py
   ```

2. **WebRTC Call:**
   Open http://localhost:3000 in your browser, grant microphone access, and click "Start Call".

## Audio Pipeline

The service implements a strict audio pipeline for Gemini compatibility:
- Browser (Opus/RTP) → Pion (PCM 48kHz) → Resample (16kHz) → FastAPI → Gemini (PCM 16kHz)
- Gemini (PCM 24kHz) → FastAPI → Pion → Resample (48kHz) → Opus/RTP → Browser
- Need gemini api for test.
