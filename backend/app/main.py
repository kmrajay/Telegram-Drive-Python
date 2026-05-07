"""Telegram Drive — Python + FastAPI backend."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .dependencies import app_state
from .routers import auth, files, folders, streaming, bandwidth, preview, search, network

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown hooks."""
    log.info("Telegram Drive backend starting…")
    yield
    # Shutdown: disconnect Telegram client
    if app_state.client is not None:
        try:
            await app_state.client.disconnect()
        except Exception:
            pass
    log.info("Telegram Drive backend stopped.")


app = FastAPI(title="Telegram Drive", version="1.2.0", lifespan=lifespan)

# ── CORS (dev mode) ──────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:1420",   # Tauri dev compat
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(folders.router)
app.include_router(streaming.router)
app.include_router(bandwidth.router)
app.include_router(preview.router)
app.include_router(search.router)
app.include_router(network.router)


# ── Log endpoint (frontend logging) ──────────────────────────────────

@app.post("/api/log")
async def log_message(message: str):
    log.info("[FRONTEND] %s", message)
    return {"logged": True}


# ── Progress SSE endpoint ───────────────────────────────────────────

@app.get("/api/events/progress")
async def progress_events():
    """SSE stream for upload/download progress (placeholder)."""
    from sse_starlette.sse import EventSourceResponse
    import asyncio
    import json

    async def event_generator():
        while True:
            await asyncio.sleep(2)
            if app_state.transfer_progress:
                data = json.dumps(app_state.transfer_progress)
                yield {"event": "progress", "data": data}

    return EventSourceResponse(event_generator())


# ── Serve React frontend (production) ────────────────────────────────

try:
    from pathlib import Path
    static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
        log.info("Serving frontend from %s", static_dir)
except Exception as e:
    log.warning("Frontend static files not mounted: %s", e)
