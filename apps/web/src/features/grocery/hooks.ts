import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    fetchGroceryLists,
    fetchGroceryList,
    createGroceryList,
    generateGroceryList,
    updateGroceryList,
    deleteGroceryList,
    addGroceryItem,
    updateGroceryItem,
    deleteGroceryItem,
    GroceryGenerateRequest
} from "@/lib/api";
import { useWorkspace } from '../workspaces/WorkspaceProvider';

export const groceryKeys = {
    all: ["grocery"] as const,
    lists: (workspaceId: string) => [...groceryKeys.all, "lists", workspaceId] as const,
    detail: (listId: string) => [...groceryKeys.all, "list", listId] as const,
};

export function useGroceryLists() {
    const { workspaceId } = useWorkspace();
    return useQuery({
        queryKey: groceryKeys.lists(workspaceId),
        queryFn: () => fetchGroceryLists(),
    });
}

export function useGroceryList(listId: string) {
    return useQuery({
        queryKey: groceryKeys.detail(listId),
        queryFn: () => fetchGroceryList(listId),
        enabled: !!listId
    });
}

export function useCreateGroceryList() {
    const queryClient = useQueryClient();
    const { workspaceId } = useWorkspace();
    return useMutation({
        mutationFn: createGroceryList,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: groceryKeys.lists(workspaceId) });
        }
    });
}

export function useGenerateGroceryList() {
    const queryClient = useQueryClient();
    const { workspaceId } = useWorkspace();
    return useMutation({
        mutationFn: (data: GroceryGenerateRequest) => generateGroceryList(data),
        onSuccess: () => {
             queryClient.invalidateQueries({ queryKey: groceryKeys.lists(workspaceId) });
        }
    });
}

export function useUpdateGroceryList() {
    const queryClient = useQueryClient();
    const { workspaceId } = useWorkspace();
    
    return useMutation({
        mutationFn: ({ id, data }: { id: string, data: { title?: string } }) => 
            updateGroceryList(id, data),
        onSuccess: (data) => {
             queryClient.invalidateQueries({ queryKey: groceryKeys.lists(workspaceId) });
             queryClient.invalidateQueries({ queryKey: groceryKeys.detail(data.id) });
        }
    });
}

export function useDeleteGroceryList() {
    const queryClient = useQueryClient();
    const { workspaceId } = useWorkspace();
    return useMutation({
        mutationFn: deleteGroceryList,
        onSuccess: () => {
             queryClient.invalidateQueries({ queryKey: groceryKeys.lists(workspaceId) });
        }
    });
}

export function useAddGroceryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ listId, data }: { listId: string, data: { display: string, position?: number } }) => 
            addGroceryItem(listId, data),
        onSuccess: (data) => {
             queryClient.invalidateQueries({ queryKey: groceryKeys.detail(data.list_id) });
        }
    });
}

export function useUpdateGroceryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ listId, itemId, data }: { listId: string, itemId: string, data: { checked?: boolean, display?: string, quantity?: number, unit?: string } }) => 
            updateGroceryItem(listId, itemId, data),
        onSuccess: (data) => {
             queryClient.invalidateQueries({ queryKey: groceryKeys.detail(data.list_id) });
        }
    });
}

export function useDeleteGroceryItem() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ listId, itemId }: { listId: string, itemId: string }) => 
            deleteGroceryItem(listId, itemId),
        onSuccess: (_, variables) => {
             queryClient.invalidateQueries({ queryKey: groceryKeys.detail(variables.listId) });
        }
    });
}
