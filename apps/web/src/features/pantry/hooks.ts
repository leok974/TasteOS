
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    fetchPantryItems,
    createPantryItem,
    updatePantryItem,
    deletePantryItem,
    CreatePantryItem,
    UpdatePantryItem
} from "@/lib/api";

export const pantryKeys = {
    all: ["pantry"] as const,
    list: (filters: { useSoon?: boolean; search?: string }) => [...pantryKeys.all, "list", filters] as const,
};

export function usePantryList(filters: { useSoon?: boolean; search?: string } = {}) {
    return useQuery({
        queryKey: pantryKeys.list(filters),
        queryFn: () => fetchPantryItems(filters),
    });
}

export function useCreatePantryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: CreatePantryItem) => createPantryItem(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: pantryKeys.all });
        },
    });
}

export function useUpdatePantryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: UpdatePantryItem }) => updatePantryItem(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: pantryKeys.all });
        },
    });
}

export function useDeletePantryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) => deletePantryItem(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: pantryKeys.all });
        },
    });
}
