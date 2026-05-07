"""Network status endpoint."""
from __future__ import annotations

import socket
from typing import Optional

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["network"])


@router.get("/network/status")
async def is_network_available():
    """Check if Telegram servers are reachable."""
    try:
        sock = socket.create_connection(("149.154.167.50", 443), timeout=2)
        sock.close()
        return {"available": True}
    except OSError:
        return {"available": False}
