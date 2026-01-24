/**
 * Cook Session API hooks for Cook Assist v1
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

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
            const response = await api.get<CookSession>(
                `/cook/session/active?recipe_id=${recipeId}`
            );
            return response.data;
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
            const response = await api.post<CookSession>("/cook/session/start", {
                recipe_id: recipeId,
            });
            return response.data;
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
            const response = await api.patch<CookSession>(
                `/cook/session/${sessionId}`,
                patch
            );
            return response.data;
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
            const response = await api.post<AssistResponse>("/cook/assist", request);
            return response.data;
        },
    });
}
