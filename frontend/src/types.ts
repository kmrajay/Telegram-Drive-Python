export interface TelegramFile {
    id: number;
    name: string;
    size: number;
    sizeStr: string;
    created_at?: string;
    type?: string;
    folder_id?: number | null;
    mime_type?: string | null;
    file_ext?: string | null;
    icon_type?: string;
}

export interface TelegramFolder {
    id: number;
    name: string;
    parent_id?: number | null;
}

export interface BandwidthStats {
    date: string;
    up_bytes: number;
    down_bytes: number;
}

export interface QueueItem {
    id: string;
    path: string;
    folderId: number | null;
    status: 'pending' | 'uploading' | 'success' | 'error' | 'cancelled';
    progress?: number;
    error?: string;
}

export interface DownloadItem {
    id: string;
    messageId: number;
    filename: string;
    folderId: number | null;
    status: 'pending' | 'downloading' | 'success' | 'error' | 'cancelled';
    progress?: number;
    error?: string;
}
