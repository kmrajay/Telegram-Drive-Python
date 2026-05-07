# Telegram Drive — Python Edition

A Python + FastAPI + React web application that turns your Telegram account into an unlimited, secure cloud storage drive.

This is a Python translation of the original [Telegram Drive](https://github.com/caamer20/Telegram-Drive) built with Tauri, Rust, and React.

## Features

- **Unlimited Cloud Storage** — Utilizing Telegram's generous cloud infrastructure
- **Media Streaming** — Stream video and audio files directly without downloading
- **PDF Viewer** — Built-in PDF support with infinite scrolling
- **Drag & Drop** — Intuitive drag-and-drop upload and file management
- **Thumbnail Previews** — Inline thumbnails for images and media files
- **Folder Management** — Create "Folders" (private Telegram Channels) to organize content
- **Privacy Focused** — API keys and data stay local. No third-party servers
- **Search** — Global search across all your Telegram Drive files

## Architecture

| Layer | Original | Python Edition |
|-------|----------|---------------|
| Backend | Rust (Tauri) | Python (FastAPI) |
| Telegram Client | Grammers | Telethon |
| Streaming Server | Actix-web | FastAPI StreamingResponse |
| Frontend | React (Tauri IPC) | React (REST API) |
| Desktop Shell | Tauri | Web browser |

## Prerequisites

- **Python 3.10+**
- **Node.js v18+**
- **Telegram API Credentials** — Get from [my.telegram.org](https://my.telegram.org)

## Quick Start

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python run.py
```

The FastAPI server starts on `http://localhost:8000`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The React dev server starts on `http://localhost:5173` and proxies API requests to the backend.

### 3. Production Build

```bash
cd frontend
npm run build
cd ../backend
python run.py
```

The backend serves the built frontend at `http://localhost:8000`.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + CORS + static files
│   │   ├── models.py         # Pydantic models
│   │   ├── dependencies.py   # Shared state, config
│   │   ├── routers/
│   │   │   ├── auth.py       # Login, connect, logout
│   │   │   ├── files.py      # File CRUD, upload, download
│   │   │   ├── folders.py    # Folder CRUD, scan
│   │   │   ├── streaming.py  # Media streaming
│   │   │   ├── bandwidth.py  # Bandwidth tracking
│   │   │   ├── preview.py    # Preview/thumbnail
│   │   │   ├── search.py     # Global search
│   │   │   └── network.py    # Network status
│   │   └── services/
│   │       ├── bandwidth.py  # BandwidthManager
│   │       ├── peer_cache.py  # Peer resolution + caching
│   │       └── preview_cache.py # Preview/thumbnail caching
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── api.ts            # REST API client (replaces Tauri invoke)
│   │   ├── components/
│   │   ├── hooks/
│   │   └── ...
│   └── ...
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/connect` | POST | Initialize Telegram client |
| `/api/connection/status` | GET | Check connection status |
| `/api/auth/request-code` | POST | Request auth code |
| `/api/auth/sign-in` | POST | Sign in with code |
| `/api/auth/check-password` | POST | 2FA password check |
| `/api/auth/logout` | POST | Sign out |
| `/api/files` | GET | List files in folder |
| `/api/files/upload` | POST | Upload file |
| `/api/files/{id}/download` | GET | Download file |
| `/api/files/{id}` | DELETE | Delete file |
| `/api/files/move` | POST | Move files between folders |
| `/api/folders` | POST | Create folder |
| `/api/folders/{id}` | DELETE | Delete folder |
| `/api/folders/scan` | GET | Scan for folders |
| `/api/bandwidth` | GET | Get bandwidth stats |
| `/api/preview/{id}` | GET | Get file preview |
| `/api/thumbnail/{id}` | GET | Get thumbnail |
| `/api/stream/{folder}/{id}` | GET | Stream media |
| `/api/search` | GET | Search files |
| `/api/network/status` | GET | Check network |

## Configuration

- **Bandwidth Limit**: 250 GB/day (configurable in `dependencies.py`)
- **Preview Cache**: 30 files, 80 MB max (configurable in `preview_cache.py`)
- **Stream Port**: 14201 (same as original)
- **Data Directory**: `data/` (or set `TG_DRIVE_DATA` env var)

## License

MIT License — same as the original project.

## Disclaimer

This application is not affiliated with Telegram FZ-LLC. Use responsibly and in accordance with Telegram's Terms of Service.
