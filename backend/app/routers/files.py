"""File CRUD — list, upload, download, delete, move."""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, FileResponse
from telethon.tl.types import DocumentAttributeFilename

from ..dependencies import app_state
from ..models import FileMetadata, MoveFilesRequest
from ..services.bandwidth import bw_manager
from ..services.peer_cache import resolve_peer
from ..services.preview_cache import preview_path

router = APIRouter(prefix="/api", tags=["files"])
log = logging.getLogger(__name__)


# ── List Files ───────────────────────────────────────────────────────

@router.get("/files")
async def get_files(folder_id: Optional[int] = Query(None)):
    if app_state.client is None:
        return []

    try:
        peer = await resolve_peer(app_state.client, folder_id, app_state.peer_cache)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    files = []
    async for msg in app_state.client.iter_messages(peer):
        if msg.media is None:
            continue

        name, size, mime, ext = _extract_media_info(msg)

        files.append(FileMetadata(
            id=msg.id,
            folder_id=folder_id,
            name=name,
            size=size,
            mime_type=mime,
            file_ext=ext,
            created_at=str(msg.date) if msg.date else "",
            icon_type="file",
        ))

    return files


# ── Upload File ──────────────────────────────────────────────────────

@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    transfer_id: Optional[str] = Form(None),
):
    if app_state.client is None:
        raise HTTPException(status_code=400, detail="Not connected")

    # Read file to temp location
    tmp_path = Path(f"tmp_upload_{uuid.uuid4().hex}")
    size = 0
    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
                size += len(chunk)

        bw_manager.can_transfer(size)

        tid = transfer_id or ""
        if tid:
            app_state.transfer_progress[tid] = 0

        # Upload via Telethon
        uploaded = await app_state.client.upload_file(str(tmp_path))
        await app_state.client.send_file(
            await resolve_peer(app_state.client, folder_id, app_state.peer_cache),
            file=uploaded,
            attributes=[DocumentAttributeFilename(file.filename or "file")],
        )

        bw_manager.add_up(size)
        if tid:
            app_state.transfer_progress[tid] = 100

        return {"status": "uploaded"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.error("Upload error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


# ── Download File ────────────────────────────────────────────────────

@router.get("/files/{message_id}/download")
async def download_file(
    message_id: int,
    folder_id: Optional[int] = Query(None),
):
    if app_state.client is None:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        peer = await resolve_peer(app_state.client, folder_id, app_state.peer_cache)
        msg = await app_state.client.get_messages(peer, ids=message_id)
        if msg is None or msg.media is None:
            raise HTTPException(status_code=404, detail="Message or media not found")

        name, size, mime, _ = _extract_media_info(msg)
        bw_manager.can_transfer(size)

        # Stream the file
        async def file_stream():
            tmp_path = Path(f"tmp_download_{uuid.uuid4().hex}")
            try:
                await app_state.client.download_media(msg, file=str(tmp_path))
                async with aiofiles.open(tmp_path, "rb") as f:
                    while chunk := await f.read(1024 * 1024):
                        yield chunk
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
            bw_manager.add_down(size)

        return StreamingResponse(
            file_stream(),
            media_type=mime or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{name}"',
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Delete File ──────────────────────────────────────────────────────

@router.delete("/files/{message_id}")
async def delete_file(
    message_id: int,
    folder_id: Optional[int] = Query(None),
):
    if app_state.client is None:
        return {"deleted": True}  # mock

    try:
        peer = await resolve_peer(app_state.client, folder_id, app_state.peer_cache)
        await app_state.client.delete_messages(peer, [message_id])
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Move Files ───────────────────────────────────────────────────────

@router.post("/files/move")
async def move_files(req: MoveFilesRequest):
    if app_state.client is None:
        return {"moved": True}  # mock

    if req.source_folder_id == req.target_folder_id:
        return {"moved": True}

    try:
        src = await resolve_peer(app_state.client, req.source_folder_id, app_state.peer_cache)
        dst = await resolve_peer(app_state.client, req.target_folder_id, app_state.peer_cache)

        await app_state.client.forward_messages(dst, req.message_ids, src)
        await app_state.client.delete_messages(src, req.message_ids)
        return {"moved": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Helpers ──────────────────────────────────────────────────────────

def _extract_media_info(msg) -> tuple[str, int, Optional[str], Optional[str]]:
    """Extract (name, size, mime, ext) from a Telethon message."""
    media = msg.media
    name = "Unknown"
    size = 0
    mime = None
    ext = None

    if hasattr(media, "document") and media.document:
        doc = media.document
        size = doc.size if hasattr(doc, "size") else 0
        mime = doc.mime_type if hasattr(doc, "mime_type") else None

        # Get filename from attributes
        for attr in (doc.attributes or []):
            if isinstance(attr, DocumentAttributeFilename):
                name = attr.file_name
                break

        if name == "Unknown" and mime:
            ext_guess = mime.split("/")[-1]
            name = f"file.{ext_guess}"

    elif hasattr(media, "photo") and media.photo:
        name = "Photo.jpg"
        size = 0
        mime = "image/jpeg"

    # Extract extension
    if name and "." in name:
        ext = name.rsplit(".", 1)[-1]

    return name, size, mime, ext
