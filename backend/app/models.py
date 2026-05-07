from pydantic import BaseModel
from typing import Optional
from enum import Enum


# ── Auth Models ──────────────────────────────────────────────────────

class AuthState(str, Enum):
    logged_out = "logged_out"
    awaiting_code = "awaiting_code"
    awaiting_password = "awaiting_password"
    logged_in = "logged_in"


class AuthResult(BaseModel):
    success: bool
    next_step: Optional[str] = None  # "code", "password", "dashboard"
    error: Optional[str] = None


class RequestCodeRequest(BaseModel):
    phone: str
    api_id: int
    api_hash: str


class SignInRequest(BaseModel):
    code: str


class CheckPasswordRequest(BaseModel):
    password: str


class ConnectRequest(BaseModel):
    api_id: int
    api_hash: Optional[str] = None


# ── File Models ──────────────────────────────────────────────────────

class FileMetadata(BaseModel):
    id: int
    folder_id: Optional[int] = None
    name: str
    size: int
    mime_type: Optional[str] = None
    file_ext: Optional[str] = None
    created_at: str
    icon_type: str = "file"


class FolderMetadata(BaseModel):
    id: int
    parent_id: Optional[int] = None
    name: str


# ── Drive Model ─────────────────────────────────────────────────────

class Drive(BaseModel):
    chat_id: int
    name: str
    icon: Optional[str] = None


# ── Bandwidth Model ─────────────────────────────────────────────────

class BandwidthStats(BaseModel):
    date: str
    up_bytes: int
    down_bytes: int


# ── Move Files Request ──────────────────────────────────────────────

class MoveFilesRequest(BaseModel):
    message_ids: list[int]
    source_folder_id: Optional[int] = None
    target_folder_id: Optional[int] = None


# ── Stream Info ──────────────────────────────────────────────────────

class StreamInfo(BaseModel):
    token: str
    base_url: str


# ── Progress ────────────────────────────────────────────────────────

class ProgressPayload(BaseModel):
    id: str
    percent: int


# ── Log Request ─────────────────────────────────────────────────────

class LogRequest(BaseModel):
    message: str


# ── Create Folder Request ────────────────────────────────────────────

class CreateFolderRequest(BaseModel):
    name: str


# ── Frontend Types (matching TypeScript) ────────────────────────────

class TelegramFile(BaseModel):
    id: int
    name: str
    size: int
    sizeStr: str
    created_at: Optional[str] = None
    type: Optional[str] = None
    folder_id: Optional[int] = None
    mime_type: Optional[str] = None
    file_ext: Optional[str] = None
    icon_type: str = "file"


class TelegramFolder(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
