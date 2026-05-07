You are translating a Tauri+Rust+React desktop app into a Python+FastAPI+React web app.

STEP 1: Read TRANSLATION_SPEC.md for full architecture instructions.

STEP 2: Read ALL the original Rust source files:
- ../telegram-drive-original/app/src-tauri/src/main.rs
- ../telegram-drive-original/app/src-tauri/src/lib.rs
- ../telegram-drive-original/app/src-tauri/src/models.rs
- ../telegram-drive-original/app/src-tauri/src/server.rs
- ../telegram-drive-original/app/src-tauri/src/bandwidth.rs
- ../telegram-drive-original/app/src-tauri/src/commands/mod.rs
- ../telegram-drive-original/app/src-tauri/src/commands/auth.rs
- ../telegram-drive-original/app/src-tauri/src/commands/fs.rs
- ../telegram-drive-original/app/src-tauri/src/commands/network.rs
- ../telegram-drive-original/app/src-tauri/src/commands/preview.rs
- ../telegram-drive-original/app/src-tauri/src/commands/streaming.rs
- ../telegram-drive-original/app/src-tauri/src/commands/utils.rs

STEP 3: Read the React frontend source files in frontend/src/ - especially hooks and types.

STEP 4: Build the complete Python backend in backend/ directory following the spec. Create ALL files listed in the spec structure.

STEP 5: Modify the React frontend in frontend/src/ to use REST API calls instead of Tauri IPC:
- Replace invoke() calls with fetch()
- Replace Tauri Store with localStorage
- Replace Tauri dialog with browser file input and download
- Replace Tauri event listeners with SSE or polling
- Remove UpdateBanner/Tauri updater references

When completely finished, run this command:
openclaw system event --text "Done: Python Telegram Drive translation complete" --mode now