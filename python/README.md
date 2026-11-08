# voxwire

Python package for [Voxwire](https://github.com/AnjalLLL/voxwire), a self-hostable system for real-time voice AI calls over WebRTC.

```bash
pip install voxwire            # client only, no dependencies
pip install "voxwire[server]"  # plus the signaling/agent server
```

## Client

```python
from voxwire import VoxwireClient

vx = VoxwireClient("http://localhost:8000", api_key="your-key")
print(vx.health())
session = vx.create_session(system_prompt="You are a helpful assistant.", metadata={"user": 42})
print(session["signaling_url"])   # ws://localhost:8000/ws/signaling/<id>?token=...
print(vx.get_session(session["session_id"])["status"])
vx.end_session(session["session_id"])
```

## CLI

```bash
voxwire serve --port 8000              # needs [server] and a running SFU
voxwire health --url http://localhost:8000
voxwire session --prompt "Be brief."
voxwire calls --limit 20              # active and recent calls
voxwire usage --days 7                # call and minute totals
```

The server reads its settings from environment variables or a `.env` file: `GEMINI_API_KEY`, `GEMINI_MODEL`, `PION_GRPC_URL`, `VOXWIRE_API_KEYS`, `VOXWIRE_SECRET`, `MAX_CONCURRENT_CALLS`, `MAX_CALL_SECONDS`, `STUN_SERVER`, `TURN_*`, `ELEVENLABS_*`. It needs the Voxwire SFU running next to it. The simplest way to get both is the [Docker deployment](https://github.com/AnjalLLL/voxwire#quickstart-self-host).

License: Apache-2.0
