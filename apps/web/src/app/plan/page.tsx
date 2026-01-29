
"use client";

import { useCurrentPlan, useGeneratePlan } from '@/features/plan/hooks';
import { PlanGrid } from '@/features/plan/PlanGrid';
import { InsightsCard } from '@/features/insights/InsightsCard';
import { UseSoonAutofillCard } from "@/features/plan/UseSoonAutofillCard";
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { format, startOfWeek, addDays } from 'date-fns';

import { Plus, Leaf, X } from 'lucide-react';
import { useState } from 'react';

export default function PlanPage() {
    const { plan, isLoading, isEmpty } = useCurrentPlan();
    const { generate, isGenerating } = useGeneratePlan();
    const [showBoostBanner, setShowBoostBanner] = useState(true);

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
            {/* Version Marker to confirm HMR */}
            <div className="hidden">v3.2.2</div>

            {plan?.meta?.boost_applied && showBoostBanner && (
                <div 
                    data-testid="plan-use-soon-banner" 
                    className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-start gap-3 relative animate-in fade-in slide-in-from-top-2"
                >
                    <div className="text-green-600 dark:text-green-400 mt-0.5">
                        <Leaf className="w-5 h-5" />
                    </div>
                    <div className="flex-1 pr-6">
                         <h3 className="text-sm font-semibold text-green-900 dark:text-green-100">
                             Optimized to use your pantry
                         </h3>
                         <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                             This week's plan prioritizes ingredients you need to use soon: {' '}
                             <span className="font-medium">
                                 {plan.meta.use_soon_used ? plan.meta.use_soon_used.slice(0, 3).join(", ") : ""}
                                 {plan.meta.use_soon_used && plan.meta.use_soon_used.length > 3 && `, +${plan.meta.use_soon_used.length - 3} more`}
                             </span>
                         </p>
                    </div>
                    <button 
                        onClick={() => setShowBoostBanner(false)}
                        className="absolute top-3 right-3 text-green-700/50 hover:text-green-800 dark:text-green-400/50 dark:hover:text-green-300"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Weekly Plan</h1>
                    <p className="text-muted-foreground mt-1">
                         {plan ? `Week of ${format(new Date(plan.week_start), 'MMMM d, yyyy')}` : 'Plan your meals'}
                    </p>
                </div>
                {(!plan || isEmpty) ? (
                     <Button onClick={handleGenerate} disabled={isGenerating}>
                        {isGenerating ? "Generating..." : "Generate Plan"}
                    </Button>
                ) : (
                    <AlertDialog>
                        <AlertDialogTrigger asChild>
                            <Button variant="outline" disabled={isGenerating}>
                                {isGenerating ? "Cooking..." : "Regenerate Week"}
                            </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                            <AlertDialogHeader>
                                <AlertDialogTitle>Regenerate Weekly Plan?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    This will overwrite your current weekly plan with new recipes. This action cannot be undone.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={handleGenerate}>Regenerate</AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 {/* Only show UseSoonAutofillCard if plan exists (meaning user has a structure to fill) */}
                 {plan && <UseSoonAutofillCard weekStart={plan.week_start} />}
                 <InsightsCard scope="workspace" windowDays={30} className="w-full" />
            </div>

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
