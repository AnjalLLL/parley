"""Voxwire: self-hostable real-time voice AI calls over WebRTC."""

__version__ = "0.1.0"

from voxwire.client import VoxwireClient, VoxwireError

__all__ = ["VoxwireClient", "VoxwireError", "__version__"]
