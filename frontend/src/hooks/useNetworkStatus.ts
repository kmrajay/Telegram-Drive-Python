import { useState, useEffect } from 'react';
import { api } from '../api';

export function useNetworkStatus(): boolean {
    const [isOnline, setIsOnline] = useState(true);

    useEffect(() => {
        const check = async () => {
            try {
                const result = await api.isNetworkAvailable();
                setIsOnline(result.available);
            } catch {
                setIsOnline(false);
            }
        };

        check();
        const interval = setInterval(check, 30000);
        return () => clearInterval(interval);
    }, []);

    return isOnline;
}
