'use client';

import React from 'react';
import { UnitsSettingsCard } from '@/features/preferences/components/UnitsSettingsCard';
import { IngredientDensitiesCard } from '@/features/preferences/components/IngredientDensitiesCard';
import { useQuery } from '@tanstack/react-query';
import { apiGet, Workspace } from '@/lib/api';
import { useWorkspace } from '@/features/workspaces/WorkspaceProvider';

export default function UnitSettingsPage() {
    const { workspaceId } = useWorkspace();
    const { data: workspaces } = useQuery({
        queryKey: ['workspaces'],
        queryFn: () => apiGet<Workspace[]>('/workspaces/'),
        enabled: !!workspaceId,
    });

    const activeWorkspace = workspaces?.find(w => w.id === workspaceId);

    return (
        <main className="container max-w-2xl mx-auto py-10 px-4">
            <h1 className="text-3xl font-bold mb-6">
                Units & Measurements
                {activeWorkspace && (
                    <span className="block text-lg font-normal text-muted-foreground mt-1">
                        {activeWorkspace.name}
                    </span>
                )}
            </h1>
            <div className="space-y-6">
                <UnitsSettingsCard />
                <IngredientDensitiesCard />
            </div>
        </main>
    );
}
