# REST API

Every `/api/*` route needs `Authorization: Bearer <key>` when `VOXWIRE_API_KEYS` is set. The full schema is also served at `/docs` (Swagger) and `/openapi.json`.

## Sessions

### `POST /api/session`

| Field | Type | Notes |
|---|---|---|
| `system_prompt` | string | up to 20k characters |
| `provider` | `gemini` \| `openai` \| `echo` | default: the first one with a key. 422 if the provider isn't configured |
| `voice`, `model` | string | provider-specific, for example the Gemini voice `"Puck"` or OpenAI `"alloy"` |
| `ttl_seconds` | int | how long the session waits for its call (10–86400, default `SESSION_TTL_SECONDS`) |
| `metadata` | object | your own data, returned everywhere |
| `tools`, `tool_webhook_url` | list, url | see [Tools](tools-and-webhooks.md) |
| `webhook_url` | url | call events |
| `record` | bool | needs `RECORDINGS_DIR` |

Returns the session plus `token`, `ice_servers` (and `signaling_url` when you use an SDK). Fails with 429 when you hit the rate limit or the concurrent call limit.

### Other routes

| Method | Path | Notes |
|---|---|---|
| GET | `/api/session/{id}` | status, duration, provider, end_reason, metadata. Works for live and ended calls |
| GET | `/api/session/{id}/transcript` | `{transcript: [{role, text, t}]}` |
| GET | `/api/session/{id}/recording/{user\|ai}` | WAV |
| DELETE | `/api/session/{id}` | ends a live call |
| GET | `/api/sessions` | active and recent calls |
| GET | `/api/usage?days=30` | calls and minutes |
| POST | `/api/call` | outbound phone call, see [Phone](phone.md) |
| GET | `/api/health` | `{status, version, active_calls}`, no auth needed |
| GET | `/metrics` | Prometheus |
