/**
 * Cook Session API hooks for Cook Assist v1
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE } from "@/lib/api";

// Helper function for API calls with workspace headers
async function cookFetch<T>(url: string, options?: RequestInit): Promise<T> {
    const headers = new Headers(options?.headers);
    headers.set('Content-Type', 'application/json');

    // Get workspace ID from localStorage (set by workspace selector)
    const workspaceId = typeof window !== 'undefined'
        ? localStorage.getItem('tasteos.workspace_id')
        : null;

    // Add workspace header if available
    if (workspaceId) {
        headers.set('X-Workspace-Id', workspaceId);
    }

    const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}

// Types matching backend responses
export interface CookSession {
    id: string;
    recipe_id: string;
    status: "active" | "completed" | "abandoned";
    started_at: string;
    current_step_index: number;
    step_checks: Record<string, Record<string, boolean>>; // {stepIndex: {bulletIndex: checked}}
    timers: Record<string, CookTimer>;
}

export interface CookTimer {
    step_index: number;
    bullet_index?: number | null;
    label: string;
    duration_sec: number;
    started_at?: string | null;
    elapsed_sec?: number; // Total elapsed time (for pause/resume)
    paused_at?: string | null; // NEW: Timestamp when paused
    state: "created" | "running" | "paused" | "done";
}

export interface AssistResponse {
    title: string;
    bullets: string[];
    confidence?: number;
    source: "rules" | "ai" | "mixed";
}

// Hook: Get active cook session for a recipe
export function useCookSessionActive(recipeId?: string) {
    return useQuery({
        queryKey: ["cook-session", "active", recipeId],
        queryFn: async () => {
            if (!recipeId) return null;
            try {
                return await cookFetch<CookSession>(
                    `/cook/session/active?recipe_id=${recipeId}`
                );
            } catch (error: any) {
                if (error.message.includes('404')) {
                    return null;
                }
                throw error;
            }
        },
        enabled: !!recipeId,
        retry: false, // Don't retry 404s
    });
}

// Hook: Start a new cook session
export function useCookSessionStart() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (recipeId: string) => {
            return cookFetch<CookSession>("/cook/session/start", {
                method: "POST",
                body: JSON.stringify({ recipe_id: recipeId }),
            });
        },
        onSuccess: (data) => {
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
        },
    });
}

// Hook: Update cook session
export function useCookSessionPatch(sessionId?: string) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (patch: {
            current_step_index?: number;
            step_checks_patch?: {
                step_index: number;
                bullet_index: number;
                checked: boolean;
            };
            timer_create?: {
                step_index: number;
                bullet_index?: number | null;
                label: string;
                duration_sec: number;
            };
            timer_action?: {
                timer_id: string;
                action: "start" | "pause" | "done" | "delete";
            };
        }) => {
            if (!sessionId) throw new Error("Session ID required");
            return cookFetch<CookSession>(`/cook/session/${sessionId}`, {
                method: "PATCH",
                body: JSON.stringify(patch),
            });
        },
        onSuccess: (data) => {
            // Update cache
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
        },
    });
}

// Hook: End cook session (complete or abandon)
export function useCookSessionEnd() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ sessionId, action }: {
            sessionId: string;
            action: "complete" | "abandon"
        }) => {
            if (!sessionId) throw new Error("Session ID required");
            return cookFetch<CookSession>(`/cook/session/${sessionId}/end?action=${action}`, {
                method: "PATCH",
            });
        },
        onSuccess: (data) => {
            // Update cache
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
        },
    });
}

// Hook: AI cooking assistance
export function useCookAssist() {
    return useMutation({
        mutationFn: async (request: {
            recipe_id: string;
            step_index: number;
            bullet_index?: number;
            intent: "substitute" | "macros" | "fix";
            payload: Record<string, any>;
        }) => {
            return cookFetch<AssistResponse>("/cook/assist", {
                method: "POST",
                body: JSON.stringify(request),
            });
        },
    });
}
