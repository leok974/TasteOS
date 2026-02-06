import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from '@/lib/api';

export interface UnitPrefs {
    system: "us" | "metric";
    rounding: "cook" | "decimal";
    decimal_places: number;
    allow_cross_type: boolean;
    density_policy: "known_only" | "common_only";
    // omit other fields for now if unused in UI
}

export interface UnitPrefsUpdate {
    system?: "us" | "metric";
    rounding?: "cook" | "decimal";
    decimal_places?: number;
    allow_cross_type?: boolean;
    density_policy?: "known_only" | "common_only";
}

export function useUnitPrefs() {
    return useQuery<UnitPrefs>({
        queryKey: ['unit_prefs'],
        queryFn: async () => {
             const headers = new Headers();
             const wsId = typeof window !== 'undefined' ? localStorage.getItem('tasteos.workspace_id') : null;
             if (wsId) headers.set('X-Workspace-Id', wsId);

             const res = await fetch(`${API_BASE}/prefs/unit`, { headers });
             if (!res.ok) throw new Error('Failed to fetch prefs');
             return res.json();
        },
        staleTime: 1000 * 60 * 5, // 5 minutes cache
    });
}

export function useUpdateUnitPrefs() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (patch: UnitPrefsUpdate) => {
             const headers = new Headers({ 'Content-Type': 'application/json' });
             const wsId = typeof window !== 'undefined' ? localStorage.getItem('tasteos.workspace_id') : null;
             if (wsId) headers.set('X-Workspace-Id', wsId);

             const res = await fetch(`${API_BASE}/prefs/unit`, {
                 method: 'PATCH',
                 headers,
                 body: JSON.stringify(patch)
             });
             if (!res.ok) throw new Error('Failed to update prefs');
             return res.json();
        },
        onSuccess: (data) => {
            queryClient.setQueryData(['unit_prefs'], data);
            queryClient.invalidateQueries({ queryKey: ['unit_prefs'] });
            // Invalidate conversions or density lookups if needed
            // queryClient.invalidateQueries({ queryKey: ['unit_conversion'] }); 
        }
    });
}

