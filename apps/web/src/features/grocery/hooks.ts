
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
        queryFn: () => fetchCurrentGroceryList(),
        retry: 1,
    });
}

export function useGenerateGrocery() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (params: { recipeIds?: string[]; planId?: string }) => generateGroceryList(params),
        onSuccess: (data) => {
            queryClient.setQueryData(groceryKeys.current(), data);
        },
    });
}

export function useUpdateGroceryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: { status?: string; qty?: number } }) =>
            updateGroceryItem(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: groceryKeys.current() });
        },
    });
}
