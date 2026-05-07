import { useState, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { QueueItem } from '../types';
import { api } from '../api';

export function useFileUpload(activeFolderId: number | null) {
    const queryClient = useQueryClient();
    const [uploadQueue, setUploadQueue] = useState<QueueItem[]>([]);
    const [processing, setProcessing] = useState(false);
    const [initialized, setInitialized] = useState(false);
    const cancelledRef = useRef<Set<string>>(new Set());

    // Load saved queue on mount
    useEffect(() => {
        if (initialized) return;
        try {
            const saved = localStorage.getItem('tg_drive_uploadQueue');
            if (saved) {
                const items = JSON.parse(saved) as QueueItem[];
                const pending = items.filter(i => i.status === 'pending');
                if (pending.length > 0) {
                    setUploadQueue(pending);
                    toast.info(`Restored ${pending.length} pending uploads`);
                }
            }
        } catch {
            // ignore
        }
        setInitialized(true);
    }, [initialized]);

    // Save queue when it changes
    useEffect(() => {
        if (!initialized) return;
        const pending = uploadQueue.filter(i => i.status === 'pending');
        localStorage.setItem('tg_drive_uploadQueue', JSON.stringify(pending));
    }, [uploadQueue, initialized]);

    // Queue Processor
    useEffect(() => {
        if (processing) return;
        const nextItem = uploadQueue.find(i => i.status === 'pending');
        if (nextItem) {
            processItem(nextItem);
        }
    }, [uploadQueue, processing]);

    const processItem = async (item: QueueItem) => {
        setProcessing(true);
        setUploadQueue(q => q.map(i => i.id === item.id ? { ...i, status: 'uploading', progress: 0 } : i));
        try {
            // Read file from path — in browser, we store File objects
            const file = (item as any).file as File;
            if (file) {
                await api.uploadFile(file, item.folderId, item.id);
            }
            if (cancelledRef.current.has(item.id)) {
                cancelledRef.current.delete(item.id);
            } else {
                setUploadQueue(q => q.map(i => i.id === item.id ? { ...i, status: 'success', progress: 100 } : i));
                queryClient.invalidateQueries({ queryKey: ['files', item.folderId] });
            }
        } catch (e) {
            if (!cancelledRef.current.has(item.id)) {
                setUploadQueue(q => q.map(i => i.id === item.id ? { ...i, status: 'error', error: String(e) } : i));
                toast.error(`Upload failed for ${item.path.split('/').pop()}: ${e}`);
            } else {
                cancelledRef.current.delete(item.id);
            }
        } finally {
            setProcessing(false);
        }
    };

    const handleManualUpload = async () => {
        try {
            const input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            input.onchange = () => {
                if (input.files) {
                    const newItems: QueueItem[] = Array.from(input.files).map((file) => ({
                        id: Math.random().toString(36).substr(2, 9),
                        path: file.name,
                        folderId: activeFolderId,
                        status: 'pending' as const,
                        file, // Store File object for upload
                    }));
                    setUploadQueue(prev => [...prev, ...newItems]);
                    toast.info(`Queued ${input.files!.length} files for upload`);
                }
            };
            input.click();
        } catch {
            toast.error("Failed to open file dialog");
        }
    };

    const cancelAll = () => {
        setUploadQueue(q => {
            const uploading = q.find(i => i.status === 'uploading');
            if (uploading) cancelledRef.current.add(uploading.id);
            return q
                .filter(i => i.status !== 'pending')
                .map(i => i.status === 'uploading' ? { ...i, status: 'cancelled' as const } : i);
        });
        toast.info('All uploads cancelled');
    };

    return {
        uploadQueue,
        setUploadQueue,
        handleManualUpload,
        cancelAll,
    };
}
