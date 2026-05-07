import { useEffect, useCallback } from 'react';

export function useKeyboardShortcuts(props: {
    onDelete?: () => void;
    onRefresh?: () => void;
    onSelectAll?: () => void;
}) {
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Delete' && props.onDelete) {
            props.onDelete();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'r' && props.onRefresh) {
            e.preventDefault();
            props.onRefresh();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'a' && props.onSelectAll) {
            e.preventDefault();
            props.onSelectAll();
        }
    }, [props]);

    useEffect(() => {
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);
}
