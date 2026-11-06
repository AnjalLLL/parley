from voxwire.core.config import settings

def get_ice_config() -> dict:
    servers = [{"urls": settings.STUN_SERVER}]
    if settings.TURN_ENABLED:
        servers.append({
            "urls": settings.TURN_URL,
            "username": settings.TURN_USERNAME,
            "credential": settings.TURN_CREDENTIAL,
        })
    return {"iceServers": servers}
