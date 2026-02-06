/**
 * Cook Session API hooks for Cook Assist v1
 */

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE, newIdemKey } from "@/lib/api";

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
    ended_at?: string | null; // Added
    servings_base: number;
    servings_target: number;
    current_step_index: number;
    step_checks: Record<string, Record<string, boolean>>; // {stepIndex: {bulletIndex: checked}}
    timers: Record<string, CookTimer>;
    hands_free?: { enabled: boolean } | null; // Added

    // Method Switching
    method_key?: string | null;
    steps_override?: any[] | null; // using any[] or RecipeStep[]
    method_tradeoffs?: Record<string, any> | null;
    method_generated_at?: string | null;

    // Adjust On The Fly
    adjustments_log?: any[];

    // Auto Step Detection
    auto_step_enabled: boolean;
    auto_step_mode?: 'suggest' | 'auto_jump';
    auto_step_suggested_index?: number | null;
    auto_step_confidence?: number | null;
    auto_step_reason?: string | null;
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
    due_at?: string | null;
    remaining_sec?: number | null;
    deleted_at?: string | null;
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
                headers: { "Idempotency-Key": newIdemKey() },
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
                mark_step_complete?: number;
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
                // Auto-Step V7
                auto_step_enabled?: boolean;
                auto_step_mode?: "suggest" | "auto_jump";
            }
        }) => {
            if (!sessionId) throw new Error("Session ID required");
            return cookFetch<CookSession>(`/cook/session/${sessionId}`, {
                method: "PATCH",
                headers: { "Idempotency-Key": newIdemKey() },
                body: JSON.stringify(patch),
            });
        },
        onSuccess: (data, variables) => {
            // Update cache
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
            // Invalidate history
            queryClient.invalidateQueries({ queryKey: ["session", data.id, "history"] });
            queryClient.invalidateQueries({ queryKey: ["cook-next"] });
            
            if (variables.patch.mark_step_complete !== undefined) {
                 queryClient.invalidateQueries({ queryKey: ["cook-session", "active"] });
            }
        },
        onError: (error) => {
            console.error("[CookSessionPatch] Mutation failed:", error);
            toast.error("Update failed: " + (error instanceof Error ? error.message : "Unknown error"));
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
            // v10: Use dedicated endpoints
            return cookFetch<CookSession>(`/cook/session/${sessionId}/${action}`, {
                method: "POST",
            });
        },
        onSuccess: (data, variables) => {
            // Update cache
            queryClient.setQueryData(
                ["cook-session", "active", data.recipe_id],
                data
            );
            // Invalidate history
            queryClient.invalidateQueries({ queryKey: ["session", data.id, "history"] });

            // If abandoned, maybe clear active state? 
            // Existing logic seems to rely on session data updates.
            if (variables.action === 'abandon') {
                // Force refresh of active session to see it's gone/done
                queryClient.invalidateQueries({ queryKey: ["cook-session", "active"] });
            }
        },
    });
}

// Hook: AI cooking assistance
import { toast } from 'sonner';

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
                headers: { "Idempotency-Key": newIdemKey() },
                body: JSON.stringify(request),
            });
        },
        onError: (err) => {
             console.error("[CookAssist] Failed:", err);
             toast.error("Assistant failed: " + (err instanceof Error ? err.message : "Unknown error"));
        }
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
                try {
                    const data = JSON.parse(e.data);

                    // Throttle invalidation a bit? React Query handles dupes well.
                    // Check type
                    if (data.type === 'session_updated' || data.type === 'timer.updated' || data.type === 'timer.created' || data.type === 'check_step' || data.type === 'uncheck_step') {
                        queryClient.invalidateQueries({ queryKey: ["cook-session", "active"] });
                        queryClient.invalidateQueries({ queryKey: ["cook-next"] });
                    }
                } catch (err) {
                    console.error("Failed to parse SSE data", err);
                }
            };

            evtSource.onerror = (e) => {
                evtSource?.close();
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

// --- V13 Timer Hooks ---

import {
    TimerCreateRequest, TimerActionRequest, TimerPatchRequest,
    cookTimerCreate, cookTimerAction, cookTimerPatch,
    fetchCookNext, CookNextResponse
} from "@/lib/api";

export function useCookTimerCreate() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ sessionId, payload }: { sessionId: string; payload: TimerCreateRequest }) =>
            cookTimerCreate(sessionId, payload),
        onSuccess: (_data, { sessionId }) => {
            queryClient.invalidateQueries({ queryKey: ["cook-session", "active"] });
        }
    });
}

export function useCookTimerAction() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ sessionId, timerId, payload }: { sessionId: string; timerId: string; payload: TimerActionRequest }) =>
            cookTimerAction(sessionId, timerId, payload),
        onSuccess: (_data, { sessionId }) => {
            queryClient.invalidateQueries({ queryKey: ["cook-session", "active"] });
        }
    });
}

export function useCookTimerPatch() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ sessionId, timerId, payload }: { sessionId: string; timerId: string; payload: TimerPatchRequest }) =>
            cookTimerPatch(sessionId, timerId, payload),
        onSuccess: (_data, { sessionId }) => {
            queryClient.invalidateQueries({ queryKey: ["cook-session", "active"] });
        }
    });
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

export function useCookSessionLog(sessionId: string | undefined) {
    return useQuery({
        queryKey: ["session", sessionId, "history"],
        queryFn: () => cookFetch<any[]>(`/cook/session/${sessionId}/events/recent`),
        enabled: !!sessionId,
    });
}

// Hook: Get session why/explanation
export function useCookSessionWhy(sessionId: string | undefined, enabled: boolean = false) {
    return useQuery({
        queryKey: ["session", sessionId, "why"],
        queryFn: async () => {
            if (!sessionId) return null;
            return cookFetch<{
                suggested_step_index: number | null;
                confidence: number;
                reason: string | null;
                signals: any[];
            }>(
                `/cook/session/${sessionId}/why`
            );
        },
        enabled: !!sessionId && enabled,
    });
}

// Hook: Undo last adjustment
export function useCookAdjustmentUndo(sessionId?: string) {
    const queryClient = useQueryClient();
    const mutation = useMutation({
        mutationFn: async () => {
            if (!sessionId) throw new Error("No session ID");
            return cookFetch<CookSession>(`/cook/session/${sessionId}/adjust/undo`, {
                method: "POST",
                body: JSON.stringify({})
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

    return {
        undoAdjustment: mutation.mutate,
        isUndoing: mutation.isPending
    };
}

// --- Cook Session Summary & Notes Hooks (v10) ---

export function useCookSessionComplete() {
    return useMutation({
        mutationFn: async (sessionId: string) => {
            return cookFetch(`/cook/session/${sessionId}/complete`, { method: "POST" });
        }
    });
}

export function useCookSessionSummary(sessionId: string | undefined, enabled: boolean = false) {
    return useQuery({
        queryKey: ["cook-session", sessionId, "summary"],
        queryFn: () => cookFetch<any>(`/cook/session/${sessionId}/summary`),
        enabled: !!sessionId && enabled
    });
}

export function useCookSummaryPolish() {
    return useMutation({
        mutationFn: async ({ sessionId, style, freeform_note }: { sessionId: string, style: string, freeform_note?: string }) => {
            return cookFetch<any>(`/cook/session/${sessionId}/summary/polish`, {
                method: "POST",
                body: JSON.stringify({ style, include_timeline: false, freeform_note })
            });
        }
    });
}

export function useCookNotesPreview() {
    return useMutation({
        mutationFn: async ({ sessionId, include, use_ai, style, freeform, polished_data }: {
            sessionId: string;
            include: any;
            use_ai?: boolean;
            style?: string;
            freeform?: string;
            polished_data?: any;
        }) => {
            return cookFetch<any>(`/cook/session/${sessionId}/notes/preview`, {
                method: "POST",
                body: JSON.stringify({ include, use_ai, style, freeform, polished_data })
            });
        }
    });
}

export function useCookNotesApply() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ sessionId, recipeId, notes, create_entry = true }: { sessionId: string, recipeId: string, notes: string[], create_entry?: boolean }) => {
            return cookFetch(`/cook/session/${sessionId}/notes/apply`, {
                method: "POST",
                body: JSON.stringify({
                    recipe_id: recipeId,
                    notes_append: notes,
                    create_entry
                })
            });
        },
        onSuccess: (_data, { recipeId }) => {
            // Invalidate recipe notes to refresh history UI
            queryClient.invalidateQueries({ queryKey: ['recipe-notes', recipeId] });
            // Also invalidate recipe details for legacy notes
            queryClient.invalidateQueries({ queryKey: ['recipes', 'detail', recipeId] });
        }
    });
}

// --- Cook Assist v13.1 ---

export function useCookNext(sessionId: string | null) {
    return useQuery({
        queryKey: ["cook-next", sessionId],
        queryFn: () => sessionId ? fetchCookNext(sessionId) : Promise.reject("No session"),
        enabled: !!sessionId,
        refetchOnWindowFocus: true
    });
}

// --- Cook Assist v13.2 Smart Step Timers ---

export interface TimerSuggestion {
    client_id: string;
    label: string;
    step_index: number;
    duration_s: number;
    reason: string; // 'minutes_est' | 'text_regex'
}

export function useTimerSuggestions(sessionId: string | null) {
    return useQuery({
        queryKey: ["cook-session", sessionId, "timer-suggestions"],
        queryFn: async () => {
            if (!sessionId) throw new Error("No session");
            const res = await cookFetch<{ suggested: TimerSuggestion[] }>(`/cook/session/${sessionId}/timers/suggested`);
            return res.suggested;
        },
        enabled: !!sessionId,
        staleTime: 1000 * 60 * 5, // Suggestions unlikely to change during session
    });
}

export function useTimerCreateFromSuggestions() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ sessionId, clientIds }: { sessionId: string; clientIds: string[] }) => {
            return cookFetch(`/cook/session/${sessionId}/timers/from-suggested`, {
                method: "POST",
                body: JSON.stringify({ client_ids: clientIds, autostart: true }),
                headers: {
                    "Idempotency-Key": newIdemKey()
                }
            });
        },
        onSuccess: (_data, { sessionId }) => {
            // Refresh session to show new timers
            queryClient.invalidateQueries({ queryKey: ["cook-session", sessionId] });
        }
    });
}
