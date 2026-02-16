
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
    recipe_total_minutes?: number;
    is_leftover: boolean;
    method_choice?: string;
    method_options_json?: any;
}

export interface PlanMeta {
    boost_applied: boolean;
    boost_reason?: string;
    expiring_ingredients?: string[];
    use_soon_used?: string[]; // Added property
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

    const { data: planData, error, isLoading } = useSWR<MealPlan | null>(
        workspaceId ? ['/plan/current', workspaceId, weekStartStr] : null,
        ([url, , date]) => apiGet<MealPlan | null>(`${url}?week_start=${date}`),
        {
            shouldRetryOnError: false,
        }
    );

    const plan = planData || null;
    const isEmpty = (plan === null) || (!plan && !isLoading && !!error);

    return {
        plan,
        isLoading,
        isError: error,
        isEmpty, // Handle both 200 null and legacy 404
        weekStart: weekStartStr
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
    const [isUpdating, setIsUpdating] = useState(false);

    // Manual mutate function
    const updateEntry = useCallback(async (entryId: string, updates: { recipe_id?: string; is_leftover?: boolean; method_choice?: string }) => {
        setIsUpdating(true);
        if (!workspaceId) {
            toast({ title: 'Error', description: 'No workspace selected.', variant: 'destructive' });
            setIsUpdating(false);
            return;
        }

        // Must match the key structure in useCurrentPlan
        const today = new Date();
        const monday = startOfWeek(today, { weekStartsOn: 1 });
        const weekStartStr = format(monday, 'yyyy-MM-dd');
        const key = ['/plan/current', workspaceId, weekStartStr];

        try {
            await apiPatch(`/plan/entries/${entryId}`, updates);
            // Re-fetch plan
            await mutate(key);
            toast({ title: 'Plan Updated', description: 'Changes saved.' });
        } catch (err) {
            console.error('Failed to update plan entry', err);
            toast({ title: 'Error', description: 'Could not update plan.', variant: 'destructive' });
        } finally {
            setIsUpdating(false);
        }
    }, [workspaceId, toast, mutate]);

    return { updateEntry, isUpdating };
}

export function useAddToPlan() {
    const { toast } = useToast();
    const { mutate } = useSWRConfig();
    const { workspaceId } = useWorkspace();
    const [isAdding, setIsAdding] = useState(false);

    const addToPlan = useCallback(async (params: { 
        recipeId: string; 
        date: string; 
        meal: string; 
        servings?: number 
    }) => {
        setIsAdding(true);
        if (!workspaceId) {
            toast({ title: 'Error', description: 'No workspace.', variant: 'destructive' });
            setIsAdding(false);
            return false;
        }

        try {
            await apiPost('/plan/entries', {
                date: params.date,
                meal: params.meal,
                recipe_id: params.recipeId,
                servings_override: params.servings || null
            });
            
            // Invalidate plan cache
            const planDate = new Date(params.date);
            const monday = startOfWeek(planDate, { weekStartsOn: 1 });
            const weekStartStr = format(monday, 'yyyy-MM-dd');
            const key = ['/plan/current', workspaceId, weekStartStr];
            
            await mutate(key);
            
            toast({ title: 'Added to Plan', description: 'Recipe added successfully.' });
            return true;
        } catch (err) {
            console.error(err);
            toast({ title: 'Error', description: 'Failed to add to plan.', variant: 'destructive' });
            return false;
        } finally {
            setIsAdding(false);
        }
    }, [workspaceId, toast, mutate]);

    return { addToPlan, isAdding };
}

