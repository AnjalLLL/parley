# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Sessions now store `system_prompt`, `voice`, `model`, `ttl_seconds` and `metadata`, and the prompt is actually sent to the AI.
- `GET /api/session/{id}` returns the status (waiting / active / ended) and the call duration. `DELETE` hangs up a live call.
- API-key auth (`VOXWIRE_API_KEYS`) and per-call HMAC tokens (`VOXWIRE_SECRET`).
- Limits: `MAX_CONCURRENT_CALLS`, `MAX_CALL_SECONDS`, `SESSION_CREATE_PER_MINUTE`, `SESSION_TTL_SECONDS`.
- `SFU_TIMEOUT_SECONDS`: calls to the SFU time out, and the WebSocket closes with code 1011 when the SFU is unreachable, instead of hanging.
- Prometheus `/metrics`, JSON logs (`LOG_FORMAT=json`), tokens redacted from logs, and CORS origins setting (`VOXWIRE_CORS_ORIGINS`).
- `VoxwireClient.get_session()`, and `create_session(**options)`.
- `voxwire calls` and `voxwire usage` CLI commands, backed by new `VoxwireClient.list_sessions()` and `usage()` methods.
- Tests for the API, auth, the pipeline (echo) and the SFU session lifecycle.

- Providers: choose `gemini`, `openai` (OpenAI Realtime) or `echo` per session. Also `voice` and `model`.
- Tool calling: `tools` + `tool_webhook_url`. The AI calls your backend mid-call through signed webhooks.
- Live transcripts (`GET /api/session/{id}/transcript`) and optional WAV recordings (`record`, `RECORDINGS_DIR`).
- Call events `call.started`, `call.ended` and `transcript.ready`, signed and retried.
- Phone calls through Twilio Media Streams: inbound `/twilio/voice`, outbound `POST /api/call`.
- SQLite call log, plus `GET /api/sessions` and `GET /api/usage`. Each API key only sees its own calls.
- Dashboard (`web/dashboard.html`): usage, calls, transcripts, recordings.
- Time-limited TURN credentials (`TURN_SECRET`). Session create returns `ice_servers`.
- Deploy profiles: `https` (Caddy), `turn` (coturn), `monitoring` (Prometheus + Grafana).
- Browser SDK on npm: `npm i voxwire`.
- Docs site (MkDocs), the `examples/voice-agents` example, and `scripts/loadtest.py`.

### Changed
- **Breaking:** the signaling WebSocket now requires a session created through `POST /api/session` and its `?token=`. Random session IDs are rejected.
- `/api/health` no longer exposes the SFU address. It now returns `version` and `active_calls`.
- The FastAPI `on_event("startup")` hook is replaced by a `lifespan` handler, which removes the deprecation warning. Startup behaviour is unchanged.

## [0.1.0] - 2026-11-06

### Added
- First public release, under the name Voxwire (previously Parley).
- `voxwire` Python package: a dependency-free `VoxwireClient`, the `voxwire` CLI, and the server behind the `[server]` extra.
- Docker images for the server and the SFU, plus a production compose file in `deploy/`.
- Echo mode for testing without a Gemini API key.
