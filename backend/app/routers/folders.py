"""Folder CRUD — create, delete, scan."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from telethon.tl.functions.channels import CreateChannelRequest, DeleteChannelRequest
from telethon.tl.types import InputPeerChannel

from ..dependencies import app_state
from ..models import FolderMetadata, CreateFolderRequest
from ..services.peer_cache import resolve_peer, _cache_peer

router = APIRouter(prefix="/api", tags=["folders"])
log = logging.getLogger(__name__)


# ── Create Folder ────────────────────────────────────────────────────

@router.post("/folders")
async def create_folder(req: CreateFolderRequest):
    if app_state.client is None:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        result = await app_state.client(
            CreateChannelRequest(
                title=f"{req.name} [TD]",
                about="Telegram Drive Storage Folder\n[telegram-drive-folder]",
                megagroup=False,
            )
        )
        # Extract channel from updates
        chat_id = 0
        for chat in (result.chats or []):
            if hasattr(chat, "id"):
                chat_id = chat.id
                _cache_peer(chat, app_state.peer_cache)
                break

        display_name = req.name
        log.info("Created folder '%s' with ID %s", display_name, chat_id)
        return FolderMetadata(id=chat_id, name=display_name)
    except Exception as e:
        log.error("Create folder error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Delete Folder ───────────────────────────────────────────────────

@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int):
    if app_state.client is None:
        raise HTTPException(status_code=400, detail="Not connected")

    try:
        peer = await resolve_peer(app_state.client, folder_id, app_state.peer_cache)
        await app_state.client(DeleteChannelRequest(channel=peer))
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Scan Folders ─────────────────────────────────────────────────────

@router.get("/folders/scan")
async def scan_folders():
    if app_state.client is None:
        return []

    folders = []
    async for dialog in app_state.client.iter_dialogs():
        entity = dialog.entity
        name = dialog.name

        # Only process channels
        if not hasattr(entity, "broadcast") and not hasattr(entity, "megagroup"):
            # Could be User or Chat — cache it anyway
            _cache_peer(entity, app_state.peer_cache)
            continue

        # Strategy 1: Title contains [TD]
        if "[td]" in name.lower():
            display_name = (
                name.replace(" [TD]", "")
                .replace(" [td]", "")
                .replace("[TD]", "")
                .replace("[td]", "")
                .strip()
            )
            eid = entity.id if hasattr(entity, "id") else 0
            folders.append(FolderMetadata(id=eid, name=display_name))
            _cache_peer(entity, app_state.peer_cache)
            continue

        # Strategy 2: About contains [telegram-drive-folder]
        try:
            full = await app_state.client(
                __import__("telethon.tl.functions.channels", fromlist=["GetFullChannelRequest"]).GetFullChannelRequest(
                    channel=entity
                )
            )
            if hasattr(full, "full_chat") and hasattr(full.full_chat, "about"):
                if "[telegram-drive-folder]" in (full.full_chat.about or ""):
                    eid = entity.id if hasattr(entity, "id") else 0
                    folders.append(FolderMetadata(id=eid, name=name))
        except Exception:
            pass

        _cache_peer(entity, app_state.peer_cache)

    log.info("Scan complete. Found %d folders. Peer cache size: %d", len(folders), len(app_state.peer_cache))
    return folders
