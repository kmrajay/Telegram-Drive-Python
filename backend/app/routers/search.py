"""Global search endpoint."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputMessagesFilterDocument

from ..dependencies import app_state
from ..models import FileMetadata
from ..routers.files import _extract_media_info

router = APIRouter(prefix="/api", tags=["search"])
log = logging.getLogger(__name__)


@router.get("/search")
async def search_global(q: str = Query(...)):
    if app_state.client is None:
        return []

    try:
        result = await app_state.client(
            SearchGlobalRequest(
                q=q,
                filter=InputMessagesFilterDocument(),
                min_date=0,
                max_date=0,
                offset_rate=0,
                offset_peer=app_state.client.get_input_entity("me"),
                offset_id=0,
                limit=50,
            )
        )

        files = []
        for msg in (result.messages or []):
            if msg.media:
                name, size, mime, ext = _extract_media_info(msg)
                folder_id = None
                if hasattr(msg, "peer_id") and msg.peer_id:
                    if hasattr(msg.peer_id, "channel_id"):
                        folder_id = msg.peer_id.channel_id
                    elif hasattr(msg.peer_id, "user_id"):
                        folder_id = msg.peer_id.user_id
                    elif hasattr(msg.peer_id, "chat_id"):
                        folder_id = msg.peer_id.chat_id

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
    except Exception as e:
        log.error("Search error: %s", e)
        return []
