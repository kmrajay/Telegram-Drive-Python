"""Media streaming endpoint — mirrors Rust's Actix streaming server."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from telethon.tl.types import DocumentAttributeFilename

from ..dependencies import app_state, STREAM_TOKEN
from ..services.bandwidth import bw_manager
from ..services.peer_cache import resolve_peer

router = APIRouter(tags=["streaming"])
log = logging.getLogger(__name__)


@router.get("/stream/{folder_id}/{message_id}")
async def stream_media(
    folder_id: str,
    message_id: int,
    token: Optional[str] = Query(None),
):
    # Validate stream token
    if token != STREAM_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing stream token")

    # Parse folder_id
    if folder_id in ("me", "home", "null"):
        fid = None
    else:
        try:
            fid = int(folder_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid folder ID")

    if app_state.client is None:
        raise HTTPException(status_code=503, detail="Telegram client not connected")

    try:
        peer = await resolve_peer(app_state.client, fid, app_state.peer_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        msg = await app_state.client.get_messages(peer, ids=message_id)
        if msg is None or msg.media is None:
            raise HTTPException(status_code=404, detail="Message or media not found")

        # Get media info
        media = msg.media
        mime = "application/octet-stream"
        size = 0

        if hasattr(media, "document") and media.document:
            doc = media.document
            size = doc.size if hasattr(doc, "size") else 0
            mime = doc.mime_type if hasattr(doc, "mime_type") else "application/octet-stream"
        elif hasattr(media, "photo") and media.photo:
            mime = "image/jpeg"

        bw_manager.can_transfer(size)

        # Stream the media
        async def media_stream():
            tmp_path = f"tmp_stream_{message_id}"
            try:
                await app_state.client.download_media(msg, file=tmp_path)
                import aiofiles
                async with aiofiles.open(tmp_path, "rb") as f:
                    while chunk := await f.read(1024 * 1024):
                        yield chunk
            finally:
                import os
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            bw_manager.add_down(size)

        return StreamingResponse(
            media_stream(),
            media_type=mime,
            headers={
                "Content-Length": str(size),
                "Accept-Ranges": "bytes",
                "Cache-Control": "private, max-age=120",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Stream error for msg %s: %s", message_id, e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Stream Info ──────────────────────────────────────────────────────

@router.get("/api/stream/info")
async def get_stream_info():
    from ..dependencies import STREAM_PORT
    return {
        "token": STREAM_TOKEN,
        "base_url": f"http://localhost:{STREAM_PORT}",
    }
