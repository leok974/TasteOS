
import { useState, useCallback } from 'react';
import useSWR, { mutate } from 'swr';

// Simple stub for toast since module is missing
const useToast = () => ({
    toast: (props: any) => console.log('Toast:', props)
});

const API_BASE = 'http://localhost:8000/api';

const fetcher = (url: string) => fetch(url).then((res) => {
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
});

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

export interface MealPlan {
    id: string;
    week_start: string;
    entries: PlanEntry[];
}

import { apiGet } from '@/lib/api';
import { useWorkspace } from '../workspaces/WorkspaceProvider';

export function useCurrentPlan() {
    const { workspaceId } = useWorkspace();
    const { data, error, isLoading } = useSWR<MealPlan>(
        workspaceId ? ['/plan/current', workspaceId] : null,
        ([url]) => apiGet<MealPlan>(url),
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
    const [isGenerating, setIsGenerating] = useState(false);

    const generate = useCallback(async (weekStart: string) => {
        setIsGenerating(true);
        try {
            const res = await fetch(`${API_BASE}/plan/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week_start: weekStart }),
            });

            if (!res.ok) throw new Error('Failed to generate plan');

            const data = await res.json();
            mutate(`${API_BASE}/plan/current`, data, false);
            toast({ title: 'Plan Generated', description: 'Your weekly meal plan is ready!' });
            return data;
        } catch (err) {
            toast({ title: 'Error', description: 'Failed to generate plan.', variant: 'destructive' });
            throw err;
        } finally {
            setIsGenerating(false);
        }
    }, [toast]);

    return { generate, isGenerating };
}

export function useUpdateEntry() {
    const { toast } = useToast();

    // We don't use useSWRMutation here to keep control over optimistic logic, 
    // or we can use it but manual cache manipulation is key.

    // Manual mutate function
    const updateEntry = useCallback(async (entryId: string, updates: { recipe_id?: string; is_leftover?: boolean; method_choice?: string }) => {
        const key = `${API_BASE}/plan/current`;

        // 1. Optimistic Update
        await mutate(key, (currentPlan: MealPlan | undefined) => {
            if (!currentPlan) return undefined;

            // Shallow copy plan and entries
            const newEntries = currentPlan.entries.map(e => {
                if (e.id === entryId) {
                    return { ...e, ...updates, recipe_title: "Loading..." }; // Optimistic title? Or just keep old?
                }
                return e;
            });

            return { ...currentPlan, entries: newEntries };
        }, false); // don't revalidate yet

        try {
            const res = await fetch(`${API_BASE}/plan/entries/${entryId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates),
            });

            if (!res.ok) throw new Error('Failed to update entry');

            const updatedEntry = await res.json();

            // 2. Real Update
            await mutate(key, (currentPlan: MealPlan | undefined) => {
                if (!currentPlan) return undefined;
                const newEntries = currentPlan.entries.map(e => e.id === entryId ? updatedEntry : e);
                return { ...currentPlan, entries: newEntries };
            }, false);

            toast({ title: 'Plan Updated', description: 'Meal updated successfully.' });

        } catch (err) {
            // 3. Rollback
            toast({ title: 'Update Failed', description: 'Could not update meal.', variant: 'destructive' });
            mutate(key); // Revalidate to get true server state
        }
    }, [toast]);

    return { updateEntry };
}
