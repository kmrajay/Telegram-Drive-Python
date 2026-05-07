/**
 * API client for Telegram Drive Python backend.
 * Replaces all Tauri invoke() calls with fetch() to the FastAPI server.
 */

const API_BASE = '';  // Same origin in production; proxied in dev

export async function apiGet<T>(path: string, params?: Record<string, string | number | null>): Promise<T> {
    const url = new URL(path, window.location.origin);
    if (params) {
        Object.entries(params).forEach(([k, v]) => {
            if (v !== null && v !== undefined) url.searchParams.set(k, String(v));
        });
    }
    const res = await fetch(url.toString());
    if (!res.ok) {
        const err = await res.text().catch(() => res.statusText);
        throw new Error(err);
    }
    return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
        const err = await res.text().catch(() => res.statusText);
        throw new Error(err);
    }
    return res.json();
}

export async function apiDelete<T>(path: string, params?: Record<string, string | number | null>): Promise<T> {
    const url = new URL(path, window.location.origin);
    if (params) {
        Object.entries(params).forEach(([k, v]) => {
            if (v !== null && v !== undefined) url.searchParams.set(k, String(v));
        });
    }
    const res = await fetch(url.toString(), { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.text().catch(() => res.statusText);
        throw new Error(err);
    }
    return res.json();
}

export async function apiUpload(path: string, file: File, folderId: number | null, transferId?: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (folderId !== null) formData.append('folder_id', String(folderId));
    if (transferId) formData.append('transfer_id', transferId);

    const res = await fetch(path, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) {
        const err = await res.text().catch(() => res.statusText);
        throw new Error(err);
    }
    return res.json();
}

// ── Typed API wrappers (replacing Tauri invoke calls) ─────────────

import type { TelegramFile, TelegramFolder, BandwidthStats } from '../types';

export const api = {
    // Auth
    connect: (apiId: number) => apiPost('/api/connect', { api_id: apiId }),
    checkConnection: () => apiGet<{ connected: boolean }>('/api/connection/status'),
    requestCode: (phone: string, apiId: number, apiHash: string) =>
        apiPost('/api/auth/request-code', { phone, api_id: apiId, api_hash: apiHash }),
    signIn: (code: string) => apiPost('/api/auth/sign-in', { code }),
    checkPassword: (password: string) => apiPost('/api/auth/check-password', { password }),
    logout: () => apiPost('/api/auth/logout'),

    // Files
    getFiles: (folderId: number | null) =>
        apiGet<TelegramFile[]>('/api/files', { folder_id: folderId }),
    uploadFile: (file: File, folderId: number | null, transferId?: string) =>
        apiUpload('/api/files/upload', file, folderId, transferId),
    deleteFile: (messageId: number, folderId: number | null) =>
        apiDelete(`/api/files/${messageId}`, { folder_id: folderId }),
    downloadFileUrl: (messageId: number, folderId: number | null) =>
        `/api/files/${messageId}/download?folder_id=${folderId ?? ''}`,
    moveFiles: (messageIds: number[], sourceFolderId: number | null, targetFolderId: number | null) =>
        apiPost('/api/files/move', {
            message_ids: messageIds,
            source_folder_id: sourceFolderId,
            target_folder_id: targetFolderId,
        }),

    // Folders
    createFolder: (name: string) => apiPost<TelegramFolder>('/api/folders', { name }),
    deleteFolder: (folderId: number) => apiDelete(`/api/folders/${folderId}`),
    scanFolders: () => apiGet<TelegramFolder[]>('/api/folders/scan'),

    // Bandwidth
    getBandwidth: () => apiGet<BandwidthStats>('/api/bandwidth'),

    // Preview
    getPreview: (messageId: number, folderId: number | null) =>
        apiGet<string>(`/api/preview/${messageId}`, { folder_id: folderId }),
    getThumbnail: (messageId: number, folderId: number | null) =>
        apiGet<string>(`/api/thumbnail/${messageId}`, { folder_id: folderId }),

    // Streaming
    getStreamInfo: () => apiGet<{ token: string; base_url: string }>('/api/stream/info'),

    // Search
    searchGlobal: (query: string) =>
        apiGet<TelegramFile[]>('/api/search', { q: query }),

    // Network
    isNetworkAvailable: () => apiGet<{ available: boolean }>('/api/network/status'),

    // Cache
    cleanCache: () => apiPost('/api/cache/clean'),

    // Log
    log: (message: string) => apiPost('/api/log', { message }),
};
