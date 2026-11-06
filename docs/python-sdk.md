# Python SDK

```bash
pip install voxwire            # client only, no dependencies
pip install "voxwire[server]"  # the server too
```

```python
from voxwire import VoxwireClient, VoxwireError

vx = VoxwireClient("https://voice.example.com", api_key="…", timeout=10)
s = vx.create_session("You are helpful.", provider="openai", voice="alloy", metadata={"user": 42})
s["signaling_url"], s["ice_servers"], s["token"]
vx.get_session(s["session_id"])     # status, duration…
vx.end_session(s["session_id"])     # hang up
vx.health()
```

`create_session` takes the same fields as [`POST /api/session`](api.md). Errors raise `VoxwireError`.

## CLI

```bash
voxwire serve --port 8000
voxwire health --url http://localhost:8000
voxwire session --prompt "Be brief." --api-key …
```
