// Minimal toast hook implementation
import { useState, useCallback } from 'react';

export interface Toast {
    id: string;
    title?: string;
    description?: string;
    variant?: 'default' | 'destructive';
}

let toastCount = 0;

export function useToast() {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const toast = useCallback(({ title, description, variant = 'default' }: Omit<Toast, 'id'>) => {
        const id = `toast-${toastCount++}`;
        const newToast: Toast = { id, title, description, variant };

        setToasts((prev) => [...prev, newToast]);

        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 3000);

        return { id };
    }, []);

    const dismiss = useCallback((toastId?: string) => {
        setToasts((prev) => {
            if (toastId) {
                return prev.filter((t) => t.id !== toastId);
            }
            return [];
        });
    }, []);

    return {
        toast,
        dismiss,
        toasts,
    };
}
