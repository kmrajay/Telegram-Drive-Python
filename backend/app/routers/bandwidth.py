"""Bandwidth tracking endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from ..services.bandwidth import bw_manager

router = APIRouter(prefix="/api", tags=["bandwidth"])


@router.get("/bandwidth")
async def get_bandwidth():
    return bw_manager.get_stats()
