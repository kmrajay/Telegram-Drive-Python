import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useConfirm } from '../context/ConfirmContext';
import { TelegramFolder } from '../types';
import { useNetworkStatus } from './useNetworkStatus';
import { api } from '../api';

// Simple localStorage-based store (replaces Tauri Store plugin)
const localStore = {
    get: <T>(key: string): T | null => {
        try {
            const v = localStorage.getItem(`tg_drive_${key}`);
            return v ? JSON.parse(v) : null;
        } catch {
            return null;
        }
    },
    set: (key: string, value: unknown) => {
        localStorage.setItem(`tg_drive_${key}`, JSON.stringify(value));
    },
    delete: (key: string) => {
        localStorage.removeItem(`tg_drive_${key}`);
    },
};

export function useTelegramConnection(onLogoutParent: () => void) {
    const queryClient = useQueryClient();
    const { confirm } = useConfirm();

    const [folders, setFolders] = useState<TelegramFolder[]>([]);
    const [activeFolderId, setActiveFolderId] = useState<number | null>(null);
    const [isSyncing, setIsSyncing] = useState(false);
    const [isConnected, setIsConnected] = useState(true);

    const networkIsOnline = useNetworkStatus();

    useEffect(() => {
        const init = async () => {
            try {
                const savedFolders = localStore.get<TelegramFolder[]>('folders');
                if (savedFolders) setFolders(savedFolders);

                const savedActiveFolderId = localStore.get<number | null>('activeFolderId');
                if (savedActiveFolderId !== null) setActiveFolderId(savedActiveFolderId);

                const apiIdStr = localStore.get<string>('api_id');
                if (apiIdStr) {
                    try {
                        const apiId = parseInt(apiIdStr);
                        await api.connect(apiId);
                        setIsConnected(true);
                        queryClient.invalidateQueries({ queryKey: ['files'] });
                    } catch {
                        const shouldRetry = window.confirm("Failed to connect to Telegram. Retry?");
                        if (shouldRetry) {
                            window.location.reload();
                        } else {
                            localStore.delete('api_id');
                            onLogoutParent();
                        }
                    }
                } else {
                    onLogoutParent();
                }
            } catch {
                // init error
            }
        };
        init();
    }, [queryClient, onLogoutParent]);

    useEffect(() => {
        setIsConnected(networkIsOnline);
    }, [networkIsOnline]);

    const isNetworkError = (error: string): boolean => {
        const keywords = ['timeout', 'connection', 'network', 'socket', 'disconnected', 'EOF', 'ECONNREFUSED', 'overflow'];
        return keywords.some(k => error.toLowerCase().includes(k.toLowerCase()));
    };

    const forceLogout = async () => {
        setIsConnected(false);
        try {
            await api.cleanCache().catch(() => {});
            localStore.delete('api_id');
            localStore.delete('api_hash');
            localStore.delete('folders');
        } catch {
            // best effort
        }
        toast.error("Connection lost. Please log in again.");
        onLogoutParent();
    };

    const handleLogout = async () => {
        if (!await confirm({ title: "Sign Out", message: "Are you sure you want to sign out? This will disconnect your active session.", confirmText: "Sign Out", variant: 'danger' })) return;

        try {
            await api.logout();
            await api.cleanCache();
            localStore.delete('api_id');
            localStore.delete('api_hash');
            localStore.delete('folders');
            onLogoutParent();
        } catch {
            toast.error("Error signing out");
            onLogoutParent();
        }
    };

    const handleSyncFolders = async () => {
        setIsSyncing(true);
        try {
            const foundFolders = await api.scanFolders();
            const merged = [...folders];
            let added = 0;
            for (const f of foundFolders) {
                if (!merged.find(existing => existing.id === f.id)) {
                    merged.push(f);
                    added++;
                }
            }
            if (added > 0) {
                setFolders(merged);
                localStore.set('folders', merged);
                toast.success(`Scan complete. Found ${added} new folders.`);
            } else {
                toast.info("Scan complete. No new folders found.");
            }
        } catch {
            toast.error("Sync failed");
        } finally {
            setIsSyncing(false);
        }
    };

    const handleCreateFolder = async (name: string) => {
        try {
            const newFolder = await api.createFolder(name);
            const updated = [...folders, newFolder];
            setFolders(updated);
            localStore.set('folders', updated);
            toast.success(`Folder "${name}" created.`);
        } catch (e) {
            toast.error("Failed to create folder: " + e);
            throw e;
        }
    };

    const handleFolderDelete = async (folderId: number, folderName: string) => {
        if (!await confirm({
            title: "Delete Folder",
            message: `Are you sure you want to delete "${folderName}"?\nThis will delete the channel on Telegram.`,
            confirmText: "Delete",
            variant: 'danger'
        })) return;

        try {
            await api.deleteFolder(folderId);
            const updated = folders.filter(f => f.id !== folderId);
            setFolders(updated);
            localStore.set('folders', updated);
            if (activeFolderId === folderId) setActiveFolderId(null);
            toast.success(`Folder "${folderName}" deleted.`);
        } catch (e: unknown) {
            const errStr = String(e);
            if (errStr.includes("not found")) {
                if (await confirm({
                    title: "Folder Not Found",
                    message: `Folder "${folderName}" not found on Telegram (it may have been deleted externally).\nRemove from this app?`,
                    confirmText: "Remove",
                    variant: 'info'
                })) {
                    const updated = folders.filter(f => f.id !== folderId);
                    setFolders(updated);
                    localStore.set('folders', updated);
                    if (activeFolderId === folderId) setActiveFolderId(null);
                }
            } else {
                toast.error(`Failed to delete folder: ${e}`);
            }
        }
    };

    const handleSetActiveFolderId = async (id: number | null) => {
        setActiveFolderId(id);
        localStore.set('activeFolderId', id);
    };

    return {
        folders,
        activeFolderId,
        setActiveFolderId: handleSetActiveFolderId,
        isSyncing,
        isConnected,
        handleLogout,
        handleSyncFolders,
        handleCreateFolder,
        handleFolderDelete,
        isNetworkError,
        forceLogout,
    };
}
