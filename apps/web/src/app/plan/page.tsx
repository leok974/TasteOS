
"use client";

import { useCurrentPlan, useGeneratePlan } from '@/features/plan/hooks';
import { PlanGrid } from '@/features/plan/PlanGrid';
import { InsightsCard } from '@/features/insights/InsightsCard';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { format, startOfWeek, addDays } from 'date-fns';

export default function PlanPage() {
    const { plan, isLoading, isEmpty } = useCurrentPlan();
    const { generate, isGenerating } = useGeneratePlan();

    const handleGenerate = () => {
        // Determine next Monday or current week's Monday
        const today = new Date();
        // For MVP, always generate for CURRENT week's Monday
        const monday = startOfWeek(today, { weekStartsOn: 1 });
        const dateStr = format(monday, 'yyyy-MM-dd');
        generate(dateStr);
    };

    return (
        <div className="container py-8 max-w-7xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Weekly Plan</h1>
                    <p className="text-muted-foreground mt-1">
                        Automated meal schedule optimized for variety and leftovers.
                    </p>
                </div>

                {(!plan || isEmpty) && (
                    <Button onClick={handleGenerate} disabled={isGenerating}>
                        {isGenerating ? "Cooking..." : "Generate New Plan"}
                    </Button>
                )}
            </div>

            <InsightsCard scope="workspace" windowDays={30} className="w-full" />

            {isLoading ? (
                <PlanSkeleton />
            ) : !plan || isEmpty ? (
                <div className="flex flex-col items-center justify-center p-20 border-2 border-dashed rounded-xl bg-muted/50">
                    <h3 className="text-xl font-semibold mb-2">No Plan for This Week</h3>
                    <p className="text-muted-foreground mb-6 max-w-md text-center">
                        Get a full week of lunches and dinners planned in seconds, using your favorites and smart leftover logic.
                    </p>
                    <Button size="lg" onClick={handleGenerate} disabled={isGenerating}>
                        {isGenerating ? "Generating..." : "Generate Plan"}
                    </Button>
                </div>
            ) : (
                <PlanGrid plan={plan} />
            )}
        </div>
    );
}

function PlanSkeleton() {
    return (
        <div className="grid grid-cols-7 gap-4">
            {[...Array(7)].map((_, i) => (
                <div key={i} className="space-y-4">
                    <Skeleton className="h-8 w-full" />
                    <Skeleton className="h-40 w-full rounded-xl" />
                    <Skeleton className="h-40 w-full rounded-xl" />
                </div>
            ))}
        </div>
    );
}
