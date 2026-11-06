# voxwire (browser client)

The browser SDK for [Voxwire](https://github.com/AnjalLLL/voxwire), for real-time voice AI calls over WebRTC. It has no dependencies, is about 3 kB, and ships with TypeScript types.

```bash
npm i voxwire
```

Your backend creates the session with its API key (see the [Python client](https://pypi.org/project/voxwire/) or the REST API). The browser only gets back `signaling_url` and `ice_servers`.

```js
import { connect } from 'voxwire';

const { signaling_url, ice_servers } = await fetch('/start-call', { method: 'POST' }).then(r => r.json());

const call = await connect(signaling_url, { iceServers: ice_servers });
document.querySelector('audio').srcObject = call.remoteStream;

call.on('ended', ({ reason }) => console.log('call ended:', reason)); // hangup, max_duration, call_limit…
muteButton.onclick = () => call.mute();   // toggles; returns the new state
hangupButton.onclick = () => call.hangup();
```

## API

| | |
|---|---|
| `connect(url, { iceServers?, stream?, timeoutMs? })` | Resolves with a `Call` once audio is flowing. Rejects if the server refuses the call or the connection fails. |
| `call.on('connected' \| 'track' \| 'ended' \| 'error', fn)` | Subscribes to an event and returns an unsubscribe function. |
| `call.remoteStream` | The AI's audio as a `MediaStream`. |
| `call.mute(muted?)`, `call.muted` | Mutes or unmutes the microphone. |
| `call.hangup()` | Ends the call and releases the microphone. |
| `call.ended` | A promise that resolves with `{ reason, code }` when the call ends. |

End reasons: `hangup`, `ended_by_api`, `max_duration`, `call_limit`, `invalid_token`, `unknown_session`, `server_error`, `ice_failed`, `timeout`, `disconnected`.

License: Apache-2.0
