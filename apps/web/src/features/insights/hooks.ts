import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchInsights, type InsightsRequest } from '@/lib/api';
import { useWorkspace } from '../workspaces/WorkspaceProvider';

export const insightKeys = {
    all: ['insights'] as const,
    detail: (scope: string, id: string | null, days: number) => [...insightKeys.all, scope, id, days] as const,
};

export function useInsights(
    scope: "workspace" | "recipe",
    recipeId: string | null = null,
    windowDays: number = 90
) {
    const { workspaceId } = useWorkspace();

    return useQuery({
        queryKey: [...insightKeys.detail(scope, recipeId, windowDays), { workspaceId }],
        queryFn: () => fetchInsights({ scope, recipe_id: recipeId, window_days: windowDays }),
        staleTime: 1000 * 60 * 60, // 1 hour (since we handle cache on backend too)
        refetchOnWindowFocus: false,
    });
}

export function useRefreshInsights() {
    const client = useQueryClient();
    const { workspaceId } = useWorkspace();

    return useMutation({
        mutationFn: async (params: InsightsRequest) => {
             return fetchInsights({ ...params, force: true });
        },
        onSuccess: (data, variables) => {
            // Update cache
            client.setQueryData(
                [...insightKeys.detail(variables.scope, variables.recipe_id || null, variables.window_days || 90), { workspaceId }],
                data
            );
        }
    });
}
