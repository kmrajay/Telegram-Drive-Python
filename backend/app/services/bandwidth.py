"""Bandwidth manager — tracks daily upload/download bytes."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..dependencies import DATA_DIR, BANDWIDTH_LIMIT_BYTES
from ..models import BandwidthStats


class BandwidthManager:
    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = file_path or DATA_DIR / "bandwidth.json"
        self.limit = BANDWIDTH_LIMIT_BYTES
        self._stats = self._load()

    # ── Persistence ──────────────────────────────────────────────────

    def _load(self) -> BandwidthStats:
        if self.file_path.exists():
            try:
                data = json.loads(self.file_path.read_text())
                return BandwidthStats(**data)
            except Exception:
                pass
        return BandwidthStats(
            date=datetime.now().strftime("%Y-%m-%d"),
            up_bytes=0,
            down_bytes=0,
        )

    def _save(self) -> None:
        self.file_path.write_text(self._stats.model_dump_json(indent=2))

    # ── Public API ───────────────────────────────────────────────────

    def check_and_reset(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if self._stats.date != today:
            self._stats.date = today
            self._stats.up_bytes = 0
            self._stats.down_bytes = 0
            self._save()

    def can_transfer(self, extra_bytes: int) -> None:
        """Raise ValueError if daily limit would be exceeded."""
        self.check_and_reset()
        total = self._stats.up_bytes + self._stats.down_bytes + extra_bytes
        if total > self.limit:
            raise ValueError(
                f"Daily bandwidth limit ({self._fmt(self.limit)}) exceeded! "
                f"Used: {self._fmt(total)}"
            )

    def add_up(self, n: int) -> None:
        self.check_and_reset()
        self._stats.up_bytes += n
        self._save()

    def add_down(self, n: int) -> None:
        self.check_and_reset()
        self._stats.down_bytes += n
        self._save()

    def get_stats(self) -> BandwidthStats:
        self.check_and_reset()
        return self._stats.model_copy()

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _fmt(b: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if b < 1024:
                return f"{b:.2f} {unit}"
            b /= 1024  # type: ignore[assignment]
        return f"{b:.2f} PB"


# Singleton
bw_manager = BandwidthManager()
