"""Signaling load test: N concurrent sessions that each open the WebSocket and hold it.

No media flows (that needs real WebRTC peers), so this measures the API, auth, session store
and SFU session setup. Run against a server in echo mode:

    uv run --project python python scripts/loadtest.py --url http://localhost:8000 --calls 50 --hold 10
"""
import argparse
import asyncio
import statistics
import time

import websockets

from voxwire import VoxwireClient


async def one_call(vx: VoxwireClient, hold: float) -> float:
    t0 = time.perf_counter()
    s = await asyncio.to_thread(vx.create_session, "load test")
    async with websockets.connect(s["signaling_url"], open_timeout=10) as ws:
        setup = time.perf_counter() - t0
        try:  # the server accepts first, then may reject (bad token, call limit) with a close code
            await asyncio.wait_for(ws.recv(), hold)
        except asyncio.TimeoutError:
            return setup  # held the call for the whole time: success
        except websockets.ConnectionClosed as e:
            raise RuntimeError(f"closed by server: {e.rcvd.code if e.rcvd else '?'} {e.rcvd.reason if e.rcvd else ''}")
    return setup


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000")
    p.add_argument("--key")
    p.add_argument("--calls", type=int, default=20)
    p.add_argument("--hold", type=float, default=5.0)
    a = p.parse_args()
    vx = VoxwireClient(a.url, api_key=a.key)
    results = await asyncio.gather(*(one_call(vx, a.hold) for _ in range(a.calls)), return_exceptions=True)
    ok = [r for r in results if isinstance(r, float)]
    errors = [r for r in results if not isinstance(r, float)]
    print(f"calls: {a.calls}  ok: {len(ok)}  failed: {len(errors)}")
    if ok:
        q = statistics.quantiles(ok, n=20) if len(ok) > 1 else ok * 19
        print(f"setup latency  p50 {statistics.median(ok) * 1000:.0f} ms  p95 {q[18] * 1000:.0f} ms")
    for e in errors[:5]:
        print("  error:", repr(e)[:160])


if __name__ == "__main__":
    asyncio.run(main())
