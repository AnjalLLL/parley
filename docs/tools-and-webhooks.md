# Tools and webhooks

## Tool calling

Give the AI tools when you create the session. When it decides to use one, Voxwire POSTs the call to your `tool_webhook_url`, and whatever JSON you return goes back to the model.

```python
vx.create_session(
    system_prompt="You are a dental receptionist. Book appointments with book_appointment.",
    tools=[{
        "name": "book_appointment",
        "description": "Book a dental appointment",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "day": {"type": "string"}},
                       "required": ["name", "day"]},
    }],
    tool_webhook_url="https://api.example.com/voxwire/tools",
)
```

Your webhook receives:

```json
{"session_id": "…", "tool": "book_appointment", "arguments": {"name": "Ana", "day": "Monday"}}
```

Reply with any JSON object, for example `{"confirmed": true, "time": "10:00"}`. If the call fails or takes longer than 10 s, the model gets `{"error": "…"}` and can tell the caller.

## Call events

Set `webhook_url` on the session, or `WEBHOOK_URL` for the whole server, to receive events:

| Event | When | `data` |
|---|---|---|
| `call.started` | Media connected | the session |
| `call.ended` | Call finished | the session, with `duration_seconds` and `end_reason` |
| `transcript.ready` | After `call.ended`, if anything was said | `{session_id, transcript: [{role, text, t}]}` |

Each event is retried 3 times with backoff.

## Verifying signatures

Every tool call and event carries `X-Voxwire-Signature: sha256=<hex>`, an HMAC-SHA256 of the raw body signed with `VOXWIRE_SECRET`:

```python
import hashlib, hmac

def valid(raw_body: bytes, header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

## Transcripts and recordings

- `GET /api/session/{id}/transcript` returns the conversation so far, or the final one after the call.
- With `RECORDINGS_DIR` set, `record: true` saves one WAV per side, which you download from `GET /api/session/{id}/recording/{user|ai}`.
