# Phone calls (Twilio)

Voxwire bridges Twilio Media Streams into the same audio pipeline, so phone callers get the same AI, tools and transcripts. Phone calls don't go through the SFU.

## Setup

1. The server has to be reachable from the internet over HTTPS. Use the `https` deploy profile or a tunnel such as ngrok.
2. Set these in `.env`:

```bash
PUBLIC_URL=https://voice.example.com
TWILIO_ACCOUNT_SID=AC…
TWILIO_AUTH_TOKEN=…
TWILIO_FROM_NUMBER=+15550000000      # for outbound calls
PHONE_SYSTEM_PROMPT=You are the receptionist at Bright Dental…
```

## Inbound calls

In the Twilio console, set your number's **Voice webhook** to `POST https://voice.example.com/twilio/voice`. Voxwire checks the `X-Twilio-Signature`, creates a session with `PHONE_SYSTEM_PROMPT`, and connects the call audio.

## Outbound calls

```bash
curl -X POST https://voice.example.com/api/call \
  -H "Authorization: Bearer $VOXWIRE_KEY" -H "Content-Type: application/json" \
  -d '{"to": "+15551234567", "system_prompt": "Remind the patient about tomorrow 10:00."}'
```

The body takes every field `POST /api/session` takes (tools, webhooks, record…) plus `to` in E.164 format.

!!! note
    Phone audio is 8 kHz μ-law, so voices sound like a phone line. Barge-in on phone calls doesn't yet cut off AI audio that Twilio has already buffered.
