# WebSocket signaling protocol

The SDKs handle this for you. This page is for writing your own client.

Connect to `/ws/signaling/{session_id}?token={token}`, then exchange JSON messages:

| Direction | Message |
|---|---|
| client → server | `{"type": "offer", "sdp": "<SDP>"}`, sent once |
| server → client | `{"type": "answer", "sdp": "<SDP>"}` |
| client → server | `{"type": "ice-candidate", "candidate": RTCIceCandidateInit}` |

Media is a single audio track in each direction (Opus).

## Close codes

| Code | Meaning |
|---|---|
| 1000 | normal hangup |
| 1011 | server error (the AI provider failed, or the media server is unavailable) |
| 4000 | ended through `DELETE /api/session/{id}` |
| 4401 | missing or invalid token |
| 4404 | unknown, expired or already-used session |
| 4408 | `MAX_CALL_SECONDS` reached |
| 4429 | concurrent call limit reached |
