"""Outgoing HTTP to the developer's backend: tool calls and call events.

Every request carries `X-Voxwire-Signature: sha256=<hex>`, an HMAC of the raw body with
VOXWIRE_SECRET, so receivers can verify it came from this server.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time

import aiohttp

from voxwire.core.config import SECRET

logger = logging.getLogger(__name__)


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()


async def _post(url: str, payload: dict, timeout: float) -> dict:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "X-Voxwire-Signature": sign(body)}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as http:
        async with http.post(url, data=body, headers=headers) as resp:
            resp.raise_for_status()
            text = await resp.text()
            return json.loads(text) if text else {}


async def call_tool(url: str, session_id: str, name: str, args: dict) -> dict:
    """Run one tool call on the developer's webhook. Errors go back to the model as {"error": ...}."""
    try:
        return await _post(url, {"session_id": session_id, "tool": name, "arguments": args}, timeout=10)
    except Exception as e:
        logger.warning(f"[{session_id}] tool {name} failed: {e}")
        return {"error": f"tool call failed: {e}"}


async def _deliver(url: str, payload: dict) -> None:
    for attempt in range(3):
        try:
            await _post(url, payload, timeout=10)
            return
        except Exception as e:
            logger.warning(f"webhook {payload['event']} attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2**attempt)
    logger.error(f"webhook {payload['event']} dropped after 3 attempts")


_pending: set[asyncio.Task] = set()


def send_event(url: str | None, event: str, data: dict) -> None:
    """Fire-and-forget event with retries; never blocks the call."""
    if not url:
        return
    task = asyncio.create_task(_deliver(url, {"event": event, "timestamp": time.time(), "data": data}))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
