
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    generateGroceryList,
    fetchCurrentGroceryList,
    updateGroceryItem,
} from "@/lib/api";

import { useWorkspace } from '../workspaces/WorkspaceProvider';

export const groceryKeys = {
    all: ["grocery"] as const,
    current: () => [...groceryKeys.all, "current"] as const,
};

export function useCurrentGrocery() {
    const { workspaceId } = useWorkspace();
    return useQuery({
        queryKey: [...groceryKeys.current(), { workspaceId }],
        queryFn: () => fetchCurrentGroceryList(true), // Always recompute on fetch for safety
        retry: 1,
    });
}

export function useGenerateGrocery() {
    const queryClient = useQueryClient();
    const { workspaceId } = useWorkspace();
    
    return useMutation({
        mutationFn: (params: { recipeIds?: string[]; planId?: string; includeEntryIds?: string[] }) => generateGroceryList(params),
        onSuccess: (data) => {
            console.log("Grocery list generated successfully:", data.id);
            // We set the data directly to preserve the ephemeral 'meta' field which is not persisted by backend
            queryClient.setQueryData([...groceryKeys.current(), { workspaceId }], data);
            
            // Optionally invalidate other grocery lists (history) if we had them
            // queryClient.invalidateQueries({ queryKey: groceryKeys.history() });
        },
        onError: (err) => {
            console.error("Failed to generate grocery list", err);
        }
    });
}

import { pantryKeys } from '../pantry/hooks';

export function useUpdateGroceryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: { status?: string; qty?: number } }) =>
            updateGroceryItem(id, data),
        onSuccess: (data, variables) => {
            queryClient.invalidateQueries({ queryKey: groceryKeys.current() });
            if (variables.data.status === 'purchased') {
                 queryClient.invalidateQueries({ queryKey: pantryKeys.all });
            }
        },
    });
}
