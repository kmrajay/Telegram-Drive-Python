"""Preview and thumbnail cache management."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from .bandwidth import bw_manager
from ..dependencies import CACHE_DIR, THUMB_DIR

PREVIEW_CACHE_MAX_FILES = 30
PREVIEW_CACHE_MAX_TOTAL_BYTES = 80 * 1024 * 1024  # 80 MB


def prune_cache(cache_dir: Path, max_files: int = PREVIEW_CACHE_MAX_FILES,
                max_bytes: int = PREVIEW_CACHE_MAX_TOTAL_BYTES) -> None:
    """Evict oldest files until within limits."""
    entries: list[tuple[Path, float, int]] = []
    for entry in cache_dir.iterdir():
        if entry.is_file():
            stat = entry.stat()
            entries.append((entry, stat.st_mtime, stat.st_size))

    entries.sort(key=lambda e: e[1])  # oldest first
    total_bytes = sum(e[2] for e in entries)

    while len(entries) > max_files or total_bytes > max_bytes:
        path, _, size = entries.pop(0)
        try:
            path.unlink()
            total_bytes -= size
        except OSError:
            break


def preview_path(folder_id: Optional[int], message_id: int, ext: str) -> Path:
    """Get the cache file path for a preview."""
    folder_key = str(folder_id) if folder_id else "home"
    return CACHE_DIR / f"{folder_key}_{message_id}.{ext}"


def thumbnail_path(message_id: int, ext: str) -> Path:
    """Get the cache file path for a thumbnail."""
    return THUMB_DIR / f"{message_id}.{ext}"


def file_to_base64_data_url(path: Path) -> Optional[str]:
    """Read a file and return as base64 data URL (images only)."""
    import base64

    ext = path.suffix.lstrip(".").lower()
    if ext not in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"):
        return None

    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif",
        "webp": "image/webp", "bmp": "image/bmp",
        "svg": "image/svg+xml",
    }
    mime = mime_map.get(ext, "image/jpeg")

    try:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode()
        return f"data:{mime};base64,{b64}"
    except OSError:
        return None


def clean_cache() -> None:
    """Remove all cached previews and thumbnails."""
    import shutil
    for d in (CACHE_DIR, THUMB_DIR):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True, exist_ok=True)
