# How it works

```
Browser ──WebRTC/Opus──▶ SFU (Go, Pion) ──gRPC PCM 16k──▶ Server (Python) ──▶ AI provider
   ▲                          │                                │
   └──── WebSocket signaling ─┴────────────────────────────────┘
Phone ──Twilio Media Stream (μ-law 8k)─────────────────────────▶ Server
```

- **Server** (`python/`, FastAPI): the REST API, WebSocket signaling, auth, sessions, and the audio pipeline to the AI provider. It also runs tool calls and sends webhooks.
- **SFU** (`sfu/`, Go/Pion): terminates WebRTC, decodes and encodes Opus, and resamples between 48 kHz and 16 kHz.
- **AI provider**: Gemini Live (16 kHz in, 24 kHz out), OpenAI Realtime (24 kHz both ways), or echo.

## Call lifecycle

1. Your backend calls `POST /api/session` with an API key. It gets back `session_id`, a short-lived `token`, `signaling_url` and `ice_servers`.
2. The browser opens `signaling_url`, sends its WebRTC offer, and gets an answer. ICE connects and audio flows.
3. The AI listens and replies. When the caller speaks over it, the AI stops (barge-in).
4. The call ends when the caller hangs up, you call `DELETE /api/session/{id}`, or `MAX_CALL_SECONDS` runs out. Voxwire then sends `call.ended` and `transcript.ready` and writes the call to the call log.

Session status moves through `waiting` → `active` → `ended`. A session can be used for one call only.
