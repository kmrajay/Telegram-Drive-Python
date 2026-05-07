# Telegram Drive - Python Translation Spec

## Goal
Translate the Rust+Tauri+React Telegram Drive app into a **Python + FastAPI + React** web application.

The original app is at `telegram-drive-original/` (read-only reference). The Python version goes in this directory.

## Architecture

### Backend: Python + FastAPI
Replace the Rust/Tauri backend with a Python FastAPI server that:
1. Serves the React frontend as static files (production build)
2. Provides REST API endpoints equivalent to all Tauri `invoke()` commands
3. Includes a streaming endpoint for media (replaces Actix server)
4. Uses **Telethon** (Python MTProto library) instead of grammers

### Frontend: React (modified)
Keep the React frontend mostly intact but:
- Replace ALL `invoke()` calls from `@tauri-apps/api/core` with `fetch()` calls to the FastAPI backend
- Replace Tauri plugin imports (`@tauri-apps/plugin-dialog`, `@tauri-apps/plugin-store`, etc.) with browser-native equivalents
- Replace `listen()` event system with SSE or polling for upload/download progress
- Use `localStorage` instead of Tauri's Store plugin
- Use native `<input type="file">` and `<a download>` instead of Tauri dialog plugin

## Backend API Endpoints (mapping from Tauri commands)

All endpoints under `/api/`:

| Tauri Command | REST Endpoint | Method | Body/Params |
|---|---|---|---|
| `cmd_connect` | `/api/connect` | POST | `{api_id}` |
| `cmd_check_connection` | `/api/connection/status` | GET | - |
| `cmd_auth_request_code` | `/api/auth/request-code` | POST | `{phone, api_id, api_hash}` |
| `cmd_auth_sign_in` | `/api/auth/sign-in` | POST | `{code}` |
| `cmd_auth_check_password` | `/api/auth/check-password` | POST | `{password}` |
| `cmd_logout` | `/api/auth/logout` | POST | - |
| `cmd_get_files` | `/api/files?folder_id={id}` | GET | query param |
| `cmd_upload_file` | `/api/files/upload` | POST | multipart form: file, folder_id, transfer_id |
| `cmd_delete_file` | `/api/files/{message_id}` | DELETE | query: folder_id |
| `cmd_download_file` | `/api/files/{message_id}/download` | GET | query: folder_id, save_path → returns file bytes |
| `cmd_move_files` | `/api/files/move` | POST | `{message_ids, source_folder_id, target_folder_id}` |
| `cmd_create_folder` | `/api/folders` | POST | `{name}` |
| `cmd_delete_folder` | `/api/folders/{folder_id}` | DELETE | - |
| `cmd_scan_folders` | `/api/folders/scan` | GET | - |
| `cmd_get_bandwidth` | `/api/bandwidth` | GET | - |
| `cmd_get_preview` | `/api/preview/{message_id}` | GET | query: folder_id → returns base64 or file |
| `cmd_get_thumbnail` | `/api/thumbnail/{message_id}` | GET | query: folder_id |
| `cmd_get_stream_info` | `/api/stream/info` | GET | - |
| `cmd_search_global` | `/api/search` | GET | query: q |
| `cmd_is_network_available` | `/api/network/status` | GET | - |
| `cmd_clean_cache` | `/api/cache/clean` | POST | - |
| `cmd_log` | `/api/log` | POST | `{message}` |

Streaming endpoint: `GET /stream/{folder_id}/{message_id}?token={token}` (same as original Actix server)

## Python Project Structure

```
backend/
  app/
    __init__.py
    main.py           # FastAPI app, startup, mount static files
    config.py         # Settings, constants
    models.py         # Pydantic models (AuthState, FileMetadata, FolderMetadata, etc.)
    dependencies.py   # Shared state, Telegram client singleton
    routers/
      __init__.py
      auth.py         # Auth endpoints
      files.py        # File CRUD + upload/download
      folders.py      # Folder CRUD
      streaming.py    # Media streaming
      bandwidth.py    # Bandwidth tracking
      preview.py      # Preview/thumbnail
      search.py       # Global search
      network.py      # Network status
    services/
      __init__.py
      telegram.py     # Telethon client management (connect, auth, reconnection)
      bandwidth.py    # BandwidthManager equivalent
      peer_cache.py   # Peer resolution + caching
      preview_cache.py # Preview/thumbnail caching
  requirements.txt
  run.py              # uvicorn entrypoint
frontend/             # React app (copied from original, modified)
```

## Key Implementation Details

### Telegram Client (Telethon)
- Use `TelegramClient` from Telethon
- Store session in `data/telegram.session` (same pattern as grammers SqliteSession)
- Handle auth flow: request_code → sign_in → check_password
- Manage client lifecycle with proper cleanup on logout
- Auto-reconnect on connection loss

### Streaming
- Use FastAPI's `StreamingResponse` for media streaming
- Generate a random token on startup for stream auth (same as original)
- Chunk-based download from Telethon's `iter_download()`

### Bandwidth Manager
- Track daily upload/download bytes in `data/bandwidth.json`
- 250GB daily limit (same as original)
- Auto-reset on new day

### Preview/Thumbnail Cache
- Cache in `data/previews/` and `data/thumbnails/`
- LRU eviction (max 30 files, 80MB total)
- Return base64 data URLs for images, file paths for other types

### Peer Cache
- In-memory dict mapping folder_id → InputPeer
- Populated on scan_folders, lazily on resolve
- Cleared on logout

### File Upload
- Accept multipart form data
- Upload to Telethon via `client.upload_file()`
- Track progress via a server-side dict, exposed via SSE endpoint

### File Download
- Stream from Telethon's `iter_download()`
- Return as StreamingResponse with proper content-type

## Frontend Modifications

### Replace Tauri invoke with fetch
Before: `await invoke('cmd_get_files', { folderId })`
After: `const res = await fetch(\`/api/files?folder_id=\${folderId}\`); return res.json()`

### Replace Tauri Store with localStorage
Before: `await store.set('api_id', value); await store.save()`
After: `localStorage.setItem('api_id', value)`

### Replace Tauri dialog with browser APIs
Before: `await open({ multiple: true })` 
After: `<input type="file" multiple />`

Before: `await save({ defaultPath: name })`
After: `<a download={name} href={url} />`

### Replace Tauri events with SSE
Before: `listen('upload-progress', callback)`
After: `EventSource('/api/events/progress')` or polling

### Replace Tauri updater
Remove UpdateBanner component entirely (web app doesn't need auto-update)

## Requirements (requirements.txt)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
telethon>=1.34.0
python-multipart>=0.0.6
aiofiles>=23.2.1
pydantic>=2.5.0
sse-starlette>=1.8.0
```

## Important Notes
- The Python backend should be a complete, working replacement for the Rust backend
- All features from the original must be preserved: auth, file management, folders, streaming, preview, search, bandwidth tracking
- The frontend should work identically from the user's perspective
- Use async/await throughout (FastAPI + Telethon are both async)
- Handle Telethon's FloodWaitError properly (return HTTP 429 with retry-after)
- Include proper CORS headers for development (localhost:5173)
- Add a proper .gitignore for Python + Node
