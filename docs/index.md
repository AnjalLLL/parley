# Voxwire

Voxwire is open-source, self-hostable infrastructure for **real-time voice AI calls**. A browser or a phone connects to it, and it streams audio to an AI model (Gemini Live or OpenAI Realtime) and plays the reply back, with turn-taking and interruptions handled for you.

- **Browser calls** over WebRTC, through a Go (Pion) SFU
- **Phone calls**, inbound and outbound, through Twilio
- **Any provider**: Gemini Live, OpenAI Realtime, or echo mode for testing without a key
- **Tool calling**: the AI calls your backend mid-call, through signed webhooks
- **Transcripts, recordings, events**, a call log and a usage dashboard
- **Self-hosted**: one `docker compose up`, Apache-2.0

| Package | Install |
|---|---|
| Python client + server | `pip install voxwire` / `pip install "voxwire[server]"` |
| Browser SDK | `npm i voxwire` |
| Docker images | `ghcr.io/anjallll/voxwire-server`, `ghcr.io/anjallll/voxwire-sfu` |

Start with the [Quickstart](quickstart.md).
