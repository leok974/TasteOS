import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { API_BASE } from '@/lib/api';
import { useWorkspace } from '@/features/workspaces/WorkspaceProvider';

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
    const { workspaceId } = useWorkspace();
    return useQuery<UnitPrefs>({
        queryKey: ['unit_prefs', workspaceId],
        queryFn: async () => {
             const headers = new Headers();
             if (workspaceId) headers.set('X-Workspace-Id', workspaceId);

             const res = await fetch(`${API_BASE}/prefs/unit`, { headers });
             if (!res.ok) throw new Error('Failed to fetch prefs');
             const data = await res.json();
             return data.unit_prefs;
        },
        staleTime: 1000 * 60 * 5, // 5 minutes cache
        enabled: !!workspaceId,
    });
}

export function useUpdateUnitPrefs() {
    const queryClient = useQueryClient();
    const { workspaceId } = useWorkspace();

    return useMutation({
        mutationFn: async (patch: UnitPrefsUpdate) => {
             const headers = new Headers({ 'Content-Type': 'application/json' });
             if (workspaceId) headers.set('X-Workspace-Id', workspaceId);

             const res = await fetch(`${API_BASE}/prefs/unit`, {
                 method: 'PATCH',
                 headers,
                 body: JSON.stringify(patch)
             });
             if (!res.ok) throw new Error('Failed to update prefs');
             const data = await res.json();
             return data.unit_prefs;
        },
        onSuccess: (data) => {
            queryClient.setQueryData(['unit_prefs', workspaceId], data);
            queryClient.invalidateQueries({ queryKey: ['unit_prefs', workspaceId] });
            // Invalidate conversions or density lookups if needed
            // queryClient.invalidateQueries({ queryKey: ['unit_conversion'] }); 
        }
    });
}

