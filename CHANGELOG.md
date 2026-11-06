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
- Tests for the API, auth, the pipeline (echo) and the SFU session lifecycle.

### Changed
- **Breaking:** the signaling WebSocket now requires a session created through `POST /api/session` and its `?token=`. Random session IDs are rejected.
- `/api/health` no longer exposes the SFU address. It now returns `version` and `active_calls`.

## [0.1.0] - 2026-11-06

### Added
- First public release, under the name Voxwire (previously Parley).
- `voxwire` Python package: a dependency-free `VoxwireClient`, the `voxwire` CLI, and the server behind the `[server]` extra.
- Docker images for the server and the SFU, plus a production compose file in `deploy/`.
- Echo mode for testing without a Gemini API key.
