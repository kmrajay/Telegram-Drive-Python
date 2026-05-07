"""Preview and thumbnail endpoints."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..dependencies import app_state
from ..services.bandwidth import bw_manager
from ..services.peer_cache import resolve_peer
from ..services.preview_cache import (
    preview_path,
    thumbnail_path,
    file_to_base64_data_url,
    prune_cache,
    CACHE_DIR,
    THUMB_DIR,
)

router = APIRouter(prefix="/api", tags=["preview"])
log = logging.getLogger(__name__)


@router.get("/preview/{message_id}")
async def get_preview(
    message_id: int,
    folder_id: Optional[int] = Query(None),
):
    if app_state.client is None:
        return ""

    try:
        peer = await resolve_peer(app_state.client, folder_id, app_state.peer_cache)
        msg = await app_state.client.get_messages(peer, ids=message_id)
        if msg is None or msg.media is None:
            raise HTTPException(status_code=404, detail="Message or media not found")

        # Determine extension
        ext = _media_ext(msg)
        path = preview_path(folder_id, message_id, ext)

        if not path.exists():
            size = _media_size(msg)
            bw_manager.can_transfer(size)
            await app_state.client.download_media(msg, file=str(path))
            bw_manager.add_down(size)
            prune_cache(CACHE_DIR)

        # Return base64 for images
        data_url = file_to_base64_data_url(path)
        if data_url:
            return data_url

        return str(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Preview error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thumbnail/{message_id}")
async def get_thumbnail(
    message_id: int,
    folder_id: Optional[int] = Query(None),
):
    if app_state.client is None:
        return ""

    # Check cache
    for entry in THUMB_DIR.iterdir():
        if entry.name.startswith(f"{message_id}."):
            data_url = file_to_base64_data_url(entry)
            if data_url:
                return data_url

    try:
        peer = await resolve_peer(app_state.client, folder_id, app_state.peer_cache)
        msg = await app_state.client.get_messages(peer, ids=message_id)
        if msg is None or msg.media is None:
            return ""

        ext = _media_ext(msg)
        if ext not in ("jpg", "jpeg", "png", "gif", "webp"):
            return ""  # not an image

        path = thumbnail_path(message_id, ext)
        await app_state.client.download_media(msg, file=str(path))

        data_url = file_to_base64_data_url(path)
        return data_url or ""
    except Exception as e:
        log.error("Thumbnail error: %s", e)
        return ""


@router.post("/cache/clean")
async def clean_cache():
    from ..services.preview_cache import clean_cache as _clean
    _clean()
    return {"cleaned": True}


# ── Helpers ──────────────────────────────────────────────────────────

def _media_ext(msg) -> str:
    media = msg.media
    if hasattr(media, "document") and media.document:
        doc = media.document
        for attr in (doc.attributes or []):
            from telethon.tl.types import DocumentAttributeFilename
            if isinstance(attr, DocumentAttributeFilename):
                name = attr.file_name
                if "." in name:
                    return name.rsplit(".", 1)[-1].lower()
        mime = doc.mime_type if hasattr(doc, "mime_type") else ""
        mime_map = {
            "image/jpeg": "jpg", "image/png": "png",
            "video/mp4": "mp4", "image/gif": "gif",
        }
        return mime_map.get(mime, "bin")
    if hasattr(media, "photo") and media.photo:
        return "jpg"
    return "bin"


def _media_size(msg) -> int:
    media = msg.media
    if hasattr(media, "document") and media.document:
        doc = media.document
        return doc.size if hasattr(doc, "size") else 0
    if hasattr(media, "photo") and media.photo:
        return 1024 * 1024  # ~1MB estimate
    return 0
