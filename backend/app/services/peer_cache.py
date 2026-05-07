"""Peer resolution and caching — mirrors Rust's resolve_peer + peer_cache."""
from __future__ import annotations

from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import (
    InputPeerUser,
    InputPeerChannel,
    InputPeerChat,
    PeerUser,
    PeerChannel,
    PeerChat,
    Dialog,
)


async def resolve_peer(
    client: TelegramClient,
    folder_id: Optional[int],
    peer_cache: dict,
) -> object:
    """
    Resolve a folder_id to a Telethon InputPeer.

    - folder_id is None  → user's own peer (Saved Messages)
    - Cache hit → return immediately
    - Cache miss → scan all dialogs, warm the cache, then return
    """
    if folder_id is None:
        me = await client.get_me()
        return InputPeerUser(user_id=me.id, access_hash=0)

    # Fast path: cache hit
    if folder_id in peer_cache:
        return peer_cache[folder_id]

    # Slow path: scan dialogs
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        input_peer = _entity_to_input_peer(entity)
        if input_peer is not None:
            _cache_peer(entity, peer_cache)
        if _peer_id(entity) == folder_id:
            return input_peer

    raise ValueError(f"Folder/Chat {folder_id} not found")


def _peer_id(entity) -> Optional[int]:
    """Extract the numeric ID from a Telethon entity."""
    if hasattr(entity, "id"):
        return entity.id
    return None


def _entity_to_input_peer(entity) -> Optional[object]:
    """Convert a Telethon entity to its InputPeer equivalent."""
    if isinstance(entity, type) and hasattr(entity, "id"):
        # Channel
        if hasattr(entity, "channel_id"):
            return InputPeerChannel(
                channel_id=entity.id,
                access_hash=getattr(entity, "access_hash", 0),
            )
        # User
        if hasattr(entity, "first_name") or hasattr(entity, "bot"):
            return InputPeerUser(
                user_id=entity.id,
                access_hash=getattr(entity, "access_hash", 0),
            )
        # Chat
        return InputPeerChat(chat_id=entity.id)

    # Telethon objects handle this via their .input_entity
    if hasattr(entity, "input_entity"):
        return entity.input_entity

    return None


def _cache_peer(entity, peer_cache: dict) -> None:
    """Add entity to peer cache if it has an ID."""
    pid = _peer_id(entity)
    if pid is not None:
        peer_cache[pid] = entity


def clear_peer_cache(peer_cache: dict) -> None:
    peer_cache.clear()
