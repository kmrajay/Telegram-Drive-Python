import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { AuthWizard } from './components/AuthWizard';
import { Dashboard } from './components/Dashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ThemeProvider } from './context/ThemeContext';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 1,
            staleTime: 30000,
        }
    }
});

function AppContent() {
    const [isLoggedIn, setIsLoggedIn] = useState(() => {
        return !!localStorage.getItem('tg_drive_api_id');
    });

    return (
        <div className="h-screen w-screen overflow-hidden">
            {isLoggedIn ? (
                <Dashboard onLogout={() => setIsLoggedIn(false)} />
            ) : (
                <AuthWizard onLogin={() => setIsLoggedIn(true)} />
            )}
            <Toaster
                position="bottom-right"
                toastOptions={{
                    style: {
                        background: 'var(--toast-bg, #1f2937)',
                        color: 'var(--toast-color, #f9fafb)',
                        border: '1px solid var(--toast-border, #374151)',
                    },
                }}
            />
        </div>
    );
}

export default function App() {
    return (
        <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <ThemeProvider>
                    <AppContent />
                </ThemeProvider>
            </QueryClientProvider>
        </ErrorBoundary>
    );
}
