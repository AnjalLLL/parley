import base64
import hashlib
import hmac
import time

from voxwire.core.config import settings


def get_ice_config(ttl: int = 3600) -> dict:
    """ICE servers for the browser. With TURN_SECRET (coturn `use-auth-secret`), each call gets
    time-limited TURN credentials instead of one shared password."""
    servers = [{"urls": settings.STUN_SERVER}]
    if settings.TURN_ENABLED and settings.TURN_URL:
        if settings.TURN_SECRET:
            username = f"{int(time.time()) + ttl}:voxwire"
            digest = hmac.new(settings.TURN_SECRET.encode(), username.encode(), hashlib.sha1).digest()
            servers.append({"urls": settings.TURN_URL, "username": username,
                            "credential": base64.b64encode(digest).decode()})
        else:
            servers.append({"urls": settings.TURN_URL, "username": settings.TURN_USERNAME,
                            "credential": settings.TURN_CREDENTIAL})
    return {"iceServers": servers}
