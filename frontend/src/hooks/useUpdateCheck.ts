/**
 * Check for app updates.
 * In the Python web version, we skip auto-update and always report no update available.
 */
export function useUpdateCheck() {
    return {
        available: false,
        version: null as string | null,
        downloading: false,
        progress: 0,
        downloadAndInstall: async () => {},
        dismissUpdate: () => {},
    };
}
