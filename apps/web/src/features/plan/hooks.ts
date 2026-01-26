
import { useState, useCallback } from 'react';
import useSWR, { useSWRConfig } from 'swr';
import { useToast } from '@/hooks/use-toast';
import { apiGet, apiPost } from '@/lib/api';
import { useWorkspace } from '../workspaces/WorkspaceProvider';

const API_BASE = 'http://localhost:8000/api';

export interface PlanEntry {
    id: string;
    date: string;
    meal_type: string;
    recipe_id?: string;
    recipe_title?: string;
    is_leftover: boolean;
    method_choice?: string;
    method_options_json?: any;
}

export interface PlanMeta {
    boost_applied: boolean;
    boost_reason?: string;
    expiring_ingredients?: string[];
}

export interface MealPlan {
    id: string;
    week_start: string;
    entries: PlanEntry[];
    meta?: PlanMeta;
}

import { format, startOfWeek } from 'date-fns';

export function useCurrentPlan() {
    const { workspaceId } = useWorkspace();
    
    // Calculate current week start consistently with generation logic
    const today = new Date();
    const monday = startOfWeek(today, { weekStartsOn: 1 });
    const weekStartStr = format(monday, 'yyyy-MM-dd');

    const { data, error, isLoading } = useSWR<MealPlan>(
        workspaceId ? ['/plan/current', workspaceId, weekStartStr] : null,
        ([url, , date]) => apiGet<MealPlan>(`${url}?week_start=${date}`),
        {
            shouldRetryOnError: false,
        }
    );

    return {
        plan: data,
        isLoading,
        isError: error,
        isEmpty: !data && !isLoading && error, // 404 treated as empty
    };
}

export function useGeneratePlan() {
    const { toast } = useToast();
    const { mutate } = useSWRConfig();
    const { workspaceId } = useWorkspace();
    const [isGenerating, setIsGenerating] = useState(false);

    const generate = useCallback(async (weekStart: string) => {
        if (!workspaceId) {
            toast({ title: 'Error', description: 'No workspace selected. Please Create or Select a Workspace.', variant: 'destructive' });
            return;
        }
        setIsGenerating(true);

        try {
            const data = await apiPost<MealPlan>('/plan/generate', { week_start: weekStart });
            
            // Update the cache with the new plan using the EXACT key structure
            await mutate(
                ['/plan/current', workspaceId, weekStart],
                data,
                false // revalidate
            );
            
            toast({ title: 'Plan Generated', description: 'Your weekly meal plan is ready!' });
            return data;
        } catch (err) {
            console.error(err);
            toast({ title: 'Error', description: 'Failed to generate plan.', variant: 'destructive' });
            throw err;
        } finally {
            setIsGenerating(false);
        }
    }, [toast, mutate, workspaceId]);

    return { generate, isGenerating };
}

import { apiPatch } from '@/lib/api';

export function useUpdateEntry() {
    const { toast } = useToast();
    const { mutate } = useSWRConfig();
    const { workspaceId } = useWorkspace();

    // Manual mutate function
    const updateEntry = useCallback(async (entryId: string, updates: { recipe_id?: string; is_leftover?: boolean; method_choice?: string }) => {
        if (!workspaceId) {
            toast({ title: 'Error', description: 'No workspace selected.', variant: 'destructive' });
            return;
        }

        // Must match the key structure in useCurrentPlan
        const today = new Date();
        const monday = startOfWeek(today, { weekStartsOn: 1 });
        const weekStartStr = format(monday, 'yyyy-MM-dd');
        const key = ['/plan/current', workspaceId, weekStartStr];

        // 1. Optimistic Update
        await mutate(key, (currentPlan: MealPlan | undefined) => {
            if (!currentPlan) return undefined;

            // Shallow copy plan and entries
            const newEntries = currentPlan.entries.map(e => {
                if (e.id === entryId) {
                    return { ...e, ...updates, recipe_title: "Loading..." }; 
                }
                return e;
            });

            return { ...currentPlan, entries: newEntries };
        }, false); // don't revalidate yet

        try {
            const updatedEntry = await apiPatch<PlanEntry>(`/plan/entries/${entryId}`, updates);

            // 2. Real Update
            await mutate(key, (currentPlan: MealPlan | undefined) => {
                if (!currentPlan) return undefined;
                const newEntries = currentPlan.entries.map(e => e.id === entryId ? updatedEntry : e);
                return { ...currentPlan, entries: newEntries };
            }, false);

            toast({ title: 'Plan Updated', description: 'Meal updated successfully.' });

        } catch (err) {
            console.error(err);
            // 3. Rollback
            toast({ title: 'Update Failed', description: 'Could not update meal.', variant: 'destructive' });
            mutate(key); // Revalidate to get true server state
        }
    }, [toast, mutate, workspaceId]);

    return { updateEntry };
}
