/**
 * Cook Session API hooks for Cook Assist v1
 */

import { useEffect } from "react";
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
    servings_base: number;
    servings_target: number;
    current_step_index: number;
    step_checks: Record<string, Record<string, boolean>>; // {stepIndex: {bulletIndex: checked}}
    timers: Record<string, CookTimer>;

    // Method Switching
    method_key?: string | null;
    steps_override?: any[] | null; // using any[] or RecipeStep[]
    method_tradeoffs?: Record<string, any> | null;
    method_generated_at?: string | null;
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
                // 404 is expected if no session is active
                if (error.message?.includes('404') || error.status === 404) {
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
export function useCookSessionPatch() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ sessionId, patch }: {
            sessionId: string;
            patch: {
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
                servings_target?: number;
            }
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
        onError: (error) => {
            console.error("[CookSessionPatch] Mutation failed:", error);
        }
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

// Hook: Subscribe to SSE events
export function useCookSessionEvents(sessionId: string | undefined) {
    const queryClient = useQueryClient();

    useEffect(() => {
        if (!sessionId) return;

        let evtSource: EventSource | null = null;
        let retryTimer: NodeJS.Timeout;

        const connect = () => {
            evtSource = new EventSource(`${API_BASE}/cook/session/${sessionId}/events`);

            evtSource.onmessage = (e) => {
                // Heartbeat or random message
            };

            evtSource.addEventListener("session", (e) => {
                try {
                    const data = JSON.parse(e.data);
                    // Update cache optimistically
                    queryClient.setQueryData(
                        ["cook-session", "active", data.recipe_id],
                        data
                    );
                } catch (err) {
                    console.error("Failed to parse SSE session data", err);
                }
            });

            evtSource.onerror = (e) => {
                // console.error("SSE Error", e);
                evtSource?.close();
                // Retry after delay
                retryTimer = setTimeout(connect, 3000);
            };
        };

        connect();

        return () => {
            evtSource?.close();
            clearTimeout(retryTimer);
        };
    }, [sessionId, queryClient]);
}

// --- Method Switcher Hooks ---

export function useCookMethods() {
    return useQuery({
        queryKey: ["cook-methods"],
        queryFn: async () => {
            return cookFetch<{ methods: any[] }>("/cook/methods");
        },
        staleTime: 1000 * 60 * 60, // 1 hour
    });
}

export function useCookMethodPreview() {
    return useMutation({
        mutationFn: async ({ sessionId, methodKey }: { sessionId: string; methodKey: string }) => {
            return cookFetch<any>(`/cook/session/${sessionId}/method/preview`, {
                method: "POST",
                body: JSON.stringify({ method_key: methodKey }),
            });
        },
    });
}

export function useCookMethodApply() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ sessionId, methodKey, steps, tradeoffs }: {
            sessionId: string;
            methodKey: string;
            steps: any[];
            tradeoffs: any
        }) => {
            return cookFetch<CookSession>(`/cook/session/${sessionId}/method/apply`, {
                method: "POST",
                body: JSON.stringify({
                    method_key: methodKey,
                    steps_override: steps,
                    method_tradeoffs: tradeoffs
                }),
            });
        },
        onSuccess: (data) => {
            // Optimistic update
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
            queryClient.invalidateQueries({ queryKey: ["cook-session", "active", data.recipe_id] });
        }
    });
}

export function useCookMethodReset() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ sessionId }: { sessionId: string }) => {
            return cookFetch<CookSession>(`/cook/session/${sessionId}/method/reset`, {
                method: "POST",
            });
        },
        onSuccess: (data) => {
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
            queryClient.invalidateQueries({ queryKey: ["cook-session", "active", data.recipe_id] });
        }
    });
}
