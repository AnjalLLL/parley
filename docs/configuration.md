# Configuration

Set these in `.env` or as environment variables. This table is generated from `python/src/voxwire/core/config.py`.

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` | `None` | unset = echo mode |
| `GEMINI_MODEL` | `"gemini-2.5-flash-native-audio-preview-09-2025"` |  |
| `PION_GRPC_URL` | `"localhost:50051"` |  |
| `SFU_TIMEOUT_SECONDS` | `5.0` |  |
| `ELEVENLABS_API_KEY` | `None` |  |
| `ELEVENLABS_VOICE_ID` | `"21m00Tcm4TlvDq8ikWAM"` |  |
| `STUN_SERVER` | `"stun:stun.l.google.com:19302"` |  |
| `TURN_ENABLED` | `False` |  |
| `TURN_URL` | `""` |  |
| `TURN_USERNAME` | `""` |  |
| `TURN_CREDENTIAL` | `""` |  |
| `VOXWIRE_API_KEYS` | `""` |  |
| `VOXWIRE_SECRET` | `""` |  |
| `VOXWIRE_CORS_ORIGINS` | `"*"` |  |
| `MAX_CONCURRENT_CALLS` | `20` |  |
| `MAX_CALL_SECONDS` | `1800` |  |
| `SESSION_TTL_SECONDS` | `600` |  |
| `SESSION_CREATE_PER_MINUTE` | `60` |  |
| `LOG_FORMAT` | `"text"` | "text" or "json" |
| `OPENAI_API_KEY` | `None` |  |
| `OPENAI_REALTIME_MODEL` | `"gpt-realtime"` |  |
| `DEFAULT_PROVIDER` | `None` | gemini / openai / echo; unset = first provider with a key |
| `WEBHOOK_URL` | `""` | default events URL when a session doesn't set webhook_url |
| `RECORDINGS_DIR` | `""` | empty = recording disabled |
| `DATA_DIR` | `"data"` | sqlite call log lives here |
| `PUBLIC_URL` | `""` | https://voice.example.com, reachable by Twilio |
| `TWILIO_ACCOUNT_SID` | `""` |  |
| `TWILIO_AUTH_TOKEN` | `""` |  |
| `TWILIO_FROM_NUMBER` | `""` |  |
| `PHONE_SYSTEM_PROMPT` | `"You are a helpful assistant answering a phone call. Keep answers short."` |  |
| `TURN_SECRET` | `""` |  |

The SFU reads `PION_PUBLIC_IP`, the public IP it advertises in ICE candidates.
