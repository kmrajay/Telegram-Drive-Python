"""Shared application state and dependencies."""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import InputPeerUser, InputPeerChannel, InputPeerChat

# ── Data Directory ───────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("TG_DRIVE_DATA", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SESSION_PATH = DATA_DIR / "telegram.session"
CACHE_DIR = DATA_DIR / "previews"
THUMB_DIR = DATA_DIR / "thumbnails"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)

# ── Streaming Config ─────────────────────────────────────────────────

STREAM_PORT = 14201
STREAM_TOKEN = secrets.token_hex(16)

# ── Bandwidth Limit ─────────────────────────────────────────────────

BANDWIDTH_LIMIT_BYTES = 250 * 1024 * 1024 * 1024  # 250 GB


# ── Application State ────────────────────────────────────────────────

class AppState:
    """Holds the Telegram client and auth tokens — equivalent to Rust's TelegramState."""

    def __init__(self) -> None:
        self.client: Optional[TelegramClient] = None
        self.api_id: Optional[int] = None
        self.api_hash: Optional[str] = None
        self.phone_code_hash: Optional[str] = None
        self.phone: Optional[str] = None
        self.password_token: Optional[object] = None
        self.peer_cache: dict[int, object] = {}
        # Progress tracking for uploads/downloads
        self.transfer_progress: dict[str, int] = {}

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected()


# Singleton
app_state = AppState()
