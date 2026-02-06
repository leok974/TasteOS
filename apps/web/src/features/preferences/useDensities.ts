import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE, apiPost, apiGet, apiDelete, apiPut } from '@/lib/api';

export interface IngredientDensity {
    id: string;
    ingredient_key: string;
    display_name: string;
    density_g_per_ml: number;
    source: string;
    updated_at: string;
}

export interface IngredientDensityUpsert {
    ingredient_name: string;
    density: {
        value: number;
        per_unit: string;
    };
}

export function useDensityList(query?: string) {
    return useQuery({
        queryKey: ['densities', query],
        queryFn: async () => {
             const params = new URLSearchParams();
             if (query) params.set('query', query);
             
             const headers = new Headers();
             const wsId = typeof window !== 'undefined' ? localStorage.getItem('tasteos.workspace_id') : null;
             if (wsId) headers.set('X-Workspace-Id', wsId);

             const res = await fetch(`${API_BASE}/units/densities?${params.toString()}`, { headers });
             if (!res.ok) throw new Error('Failed to fetch densities');
             const data = await res.json();
             return data.items as IngredientDensity[];
        }
    });
}

export function useDensityUpsert() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (data: IngredientDensityUpsert) => {
             const headers = new Headers({ 'Content-Type': 'application/json' });
             const wsId = typeof window !== 'undefined' ? localStorage.getItem('tasteos.workspace_id') : null;
             if (wsId) headers.set('X-Workspace-Id', wsId);

             const res = await fetch(`${API_BASE}/units/densities`, {
                 method: 'PUT',
                 headers,
                 body: JSON.stringify(data)
             });
             if (!res.ok) throw new Error('Failed to save density');
             return res.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['densities'] });
            // Invalidate conversions if cached?
        }
    });
}
