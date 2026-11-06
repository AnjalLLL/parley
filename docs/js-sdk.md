# JavaScript SDK

```bash
npm i voxwire
```

```js
import { connect } from 'voxwire';

const call = await connect(signalingUrl, { iceServers });  // from your backend
audio.srcObject = call.remoteStream;

call.on('ended', ({ reason, code }) => {});
call.mute();          // toggle, returns the new muted state
call.hangup();
await call.ended;
```

| Option | Default | |
|---|---|---|
| `iceServers` | Google STUN | pass `session.ice_servers` |
| `stream` | asks for the mic | use your own `MediaStream` (it won't be stopped on hangup) |
| `timeoutMs` | 15000 | reject if audio isn't flowing by then |

End reasons: `hangup`, `ended_by_api`, `max_duration`, `call_limit`, `invalid_token`, `unknown_session`, `server_error`, `ice_failed`, `timeout`, `disconnected`.

There's a full working page in [`examples/voice-agents`](https://github.com/AnjalLLL/voxwire/tree/main/examples/voice-agents).
