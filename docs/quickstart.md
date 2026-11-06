# Quickstart

## 1. Run Voxwire

```bash
git clone https://github.com/AnjalLLL/voxwire && cd voxwire
cp .env.example .env          # add GEMINI_API_KEY, or leave it empty for echo mode
docker compose up --build
```

Open http://localhost:3000 and press **Start call**. In echo mode you'll hear yourself back. With a key, you'll talk to the AI.

## 2. Create calls from your backend

In production, set `VOXWIRE_API_KEYS` and `VOXWIRE_SECRET` in `.env`. Your backend then creates each call:

```python
from voxwire import VoxwireClient

vx = VoxwireClient("http://localhost:8000", api_key="your-key")
session = vx.create_session(system_prompt="You are a friendly support agent.")
# send session["signaling_url"] and session["ice_servers"] to the browser
```

## 3. Connect from the browser

```js
import { connect } from 'voxwire';

const call = await connect(signalingUrl, { iceServers });
audioElement.srcObject = call.remoteStream;
call.on('ended', ({ reason }) => console.log(reason));
```

That's a full call. Next, see [Tools and webhooks](tools-and-webhooks.md) to let the AI act on your systems, or [Self-hosting](self-hosting.md) to put it on a server.
