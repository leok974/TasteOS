'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { WorkspaceProvider } from '@/features/workspaces/WorkspaceProvider';

import { Toaster } from '@/components/ui/toaster';

export function Providers({ children }: { children: ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 60 * 1000, // 1 minute
                        refetchOnWindowFocus: false,
                    },
                },
            })
    );

    return (
        <QueryClientProvider client={queryClient}>
            <WorkspaceProvider>
                {children}
            </WorkspaceProvider>
            <Toaster />
        </QueryClientProvider>
    );
}
