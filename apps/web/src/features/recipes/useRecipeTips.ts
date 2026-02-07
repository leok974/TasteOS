import { useMutation, useQuery } from "@tanstack/react-query";
import { apiPost } from "@/lib/api";

export interface RecipeTipsResponse {
    tips: string[];
    food_safety: string[];
    confidence: "high" | "medium" | "low";
    source: "ai" | "heuristic" | "mock";
}

async function fetchRecipeTips(recipeId: string, scope: string): Promise<RecipeTipsResponse> {
    // Note: apiPost returns the parsed JSON directly (Promise<T>), not { data: T }
    // Path should be relative to API_BASE (/api), so we use "/ai/recipe_tips"
    return apiPost<RecipeTipsResponse>("/ai/recipe_tips", { recipe_id: recipeId, scope });
}

export function useRecipeTips(recipeId: string, scope: "storage" | "reheat") {
    return useQuery({
        queryKey: ["recipe-tips", recipeId, scope],
        queryFn: () => fetchRecipeTips(recipeId, scope),
        staleTime: 1000 * 60 * 60 * 24 * 30, // 30 days
        enabled: !!recipeId,
    });
}
