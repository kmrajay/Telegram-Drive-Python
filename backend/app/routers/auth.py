"""Auth endpoints — connect, request code, sign in, check password, logout."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    AuthRestartError,
)

from ..dependencies import app_state, SESSION_PATH
from ..models import (
    AuthResult,
    RequestCodeRequest,
    SignInRequest,
    CheckPasswordRequest,
    ConnectRequest,
)
from ..services.peer_cache import clear_peer_cache

router = APIRouter(prefix="/api", tags=["auth"])
log = logging.getLogger(__name__)


# ── Connect ──────────────────────────────────────────────────────────

@router.post("/connect")
async def connect(req: ConnectRequest):
    """Initialize the Telegram client with the given API ID."""
    app_state.api_id = req.api_id
    if req.api_hash:
        app_state.api_hash = req.api_hash

    if app_state.client is not None and app_state.client.is_connected():
        return {"connected": True}

    try:
        client = TelegramClient(
            str(SESSION_PATH),
            req.api_id,
            app_state.api_hash or "",
        )
        await client.connect()
        app_state.client = client
        log.info("Connected to Telegram (api_id=%s)", req.api_id)
        return {"connected": True}
    except Exception as e:
        log.error("Connection failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Check Connection ─────────────────────────────────────────────────

@router.get("/connection/status")
async def check_connection():
    """Check if the Telegram client is alive; attempt reconnect if not."""
    if app_state.client is not None and app_state.client.is_connected():
        try:
            await app_state.client.get_me()
            return {"connected": True}
        except Exception:
            log.warning("Connection check failed, attempting reconnect...")

    # Try reconnect
    if app_state.api_id is not None:
        try:
            client = TelegramClient(
                str(SESSION_PATH),
                app_state.api_id,
                app_state.api_hash or "",
            )
            await client.connect()
            app_state.client = client
            me = await client.get_me()
            if me:
                log.info("Auto-reconnect successful.")
                return {"connected": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Auto-reconnect failed: {e}")

    return {"connected": False}


# ── Request Code ─────────────────────────────────────────────────────

@router.post("/auth/request-code")
async def request_code(req: RequestCodeRequest):
    if not req.api_hash or not req.api_hash.strip():
        raise HTTPException(status_code=400, detail="API Hash cannot be empty.")

    app_state.api_id = req.api_id
    app_state.api_hash = req.api_hash

    # Disconnect any existing client first
    if app_state.client is not None:
        try:
            await app_state.client.disconnect()
        except Exception:
            pass
        app_state.client = None

    # Create fresh client and connect
    try:
        client = TelegramClient(
            str(SESSION_PATH),
            req.api_id,
            req.api_hash,
        )
        await client.connect()
        app_state.client = client
        log.info("Created and connected Telegram client for api_id=%s", req.api_id)
    except Exception as e:
        log.error("Failed to connect Telegram client: %s", e)
        raise HTTPException(status_code=500, detail=f"Connection failed: {e}")

    # Check if already logged in
    try:
        me = await client.get_me()
        if me:
            log.info("Already logged in as %s", getattr(me, 'first_name', 'user'))
            return {"status": "already_logged_in"}
    except Exception:
        pass  # Not logged in, continue with code request

    # Send code request
    try:
        result = await client.send_code_request(req.phone)
        app_state.phone_code_hash = result.phone_code_hash
        app_state.phone = req.phone
        log.info("Code requested for %s", req.phone)
        return {"status": "code_sent"}
    except FloodWaitError as e:
        raise HTTPException(status_code=429, detail=f"FLOOD_WAIT_{e.seconds}")
    except AuthRestartError:
        # Retry once
        try:
            result = await client.send_code_request(req.phone)
            app_state.phone_code_hash = result.phone_code_hash
            app_state.phone = req.phone
            return {"status": "code_sent"}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))
    except Exception as e:
        log.error("Code request failed: %s", e)
        raise HTTPException(status_code=500, detail=_map_error(e))


# ── Sign In ──────────────────────────────────────────────────────────

@router.post("/auth/sign-in")
async def sign_in(req: SignInRequest):
    if app_state.client is None:
        raise HTTPException(status_code=400, detail="Client not initialized")

    try:
        await app_state.client.sign_in(
            phone=app_state.phone,
            code=req.code,
            phone_code_hash=app_state.phone_code_hash,
        )
        log.info("Successfully logged in.")
        return AuthResult(success=True, next_step="dashboard")
    except SessionPasswordNeededError:
        app_state.password_token = True  # flag that 2FA is needed
        return AuthResult(success=False, next_step="password")
    except Exception as e:
        log.error("Sign in error: %s", e)
        raise HTTPException(status_code=401, detail=_map_error(e))


# ── Check 2FA Password ───────────────────────────────────────────────

@router.post("/auth/check-password")
async def check_password(req: CheckPasswordRequest):
    if app_state.client is None:
        raise HTTPException(status_code=400, detail="Client not initialized")

    try:
        await app_state.client.sign_in(password=req.password)
        log.info("2FA login successful.")
        return AuthResult(success=True, next_step="dashboard")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"2FA Failed: {e}")


# ── Logout ──────────────────────────────────────────────────────────

@router.post("/auth/logout")
async def logout():
    log.info("Logging out...")
    if app_state.client is not None:
        try:
            await app_state.client.log_out()
        except Exception:
            pass
        try:
            await app_state.client.disconnect()
        except Exception:
            pass

    app_state.client = None
    app_state.api_id = None
    app_state.api_hash = None
    app_state.phone_code_hash = None
    app_state.phone = None
    app_state.password_token = None
    clear_peer_cache(app_state.peer_cache)

    # Remove session file
    for suffix in ("", "-wal", "-shm"):
        p = SESSION_PATH.parent / (SESSION_PATH.name + suffix)
        if p.exists():
            p.unlink()

    log.info("Logout complete.")
    return {"logged_out": True}


# ── Helpers ──────────────────────────────────────────────────────────

def _map_error(e: Exception) -> str:
    msg = str(e)
    if "FLOOD_WAIT" in msg.upper():
        return "FLOOD_WAIT_60"
    return msg
