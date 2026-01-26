import React from 'react';
import { useInsights, useRefreshInsights } from './hooks';
import { Button } from '@/components/ui/button';
import { RefreshCw, Sparkles, Lightbulb, Target, BookOpen, AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

interface InsightsCardProps {
    scope: "workspace" | "recipe";
    recipeId?: string;
    windowDays?: number;
    className?: string;
}

export function InsightsCard({ scope, recipeId, windowDays = 90, className }: InsightsCardProps) {
    const { data, isLoading, isError } = useInsights(scope, recipeId || null, windowDays);
    const refreshMutation = useRefreshInsights();

    const handleRefresh = () => {
        refreshMutation.mutate({ scope, recipe_id: recipeId, window_days: windowDays });
    };

    if (isLoading) {
        return (
            <div className={`p-6 bg-white rounded-xl border border-stone-100 shadow-sm ${className}`}>
                <div className="flex items-center gap-2 mb-4">
                    <Skeleton className="h-5 w-5 rounded-full" />
                    <Skeleton className="h-5 w-40" />
                </div>
                <div className="space-y-3">
                    <Skeleton className="h-16 w-full rounded-lg" />
                    <Skeleton className="h-16 w-full rounded-lg" />
                    <Skeleton className="h-16 w-full rounded-lg" />
                </div>
            </div>
        );
    }

    if (isError || !data) {
        return (
            <div className={`p-6 bg-white rounded-xl border border-stone-100 shadow-sm ${className}`}>
                <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-stone-800 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-amber-500" />
                        Insights
                    </h3>
                    <Button variant="ghost" size="sm" onClick={handleRefresh}>
                        {refreshMutation.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : "Retry"}
                    </Button>
                </div>
                <p className="text-sm text-stone-500 mt-2">
                    Could not load insights at this time.
                </p>
            </div>
        );
    }

    return (
        <div className={`bg-gradient-to-br from-white to-stone-50 rounded-xl border border-stone-200 shadow-sm overflow-hidden ${className}`}>
            {/* Header */}
            <div className="p-4 border-b border-stone-100 flex items-start justify-between bg-white/50 backdrop-blur-sm">
                <div>
                   <h3 className="font-bold text-stone-800 flex items-center gap-2 text-lg">
                        <Sparkles className="w-5 h-5 text-amber-500 fill-amber-500/20" />
                        {data.headline}
                    </h3>
                    <p className="text-xs text-stone-400 mt-1 pl-7">
                        Based on history • {data.model || "heuristic"}
                    </p>
                </div>
                <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={handleRefresh}
                    disabled={refreshMutation.isPending}
                    className="text-stone-400 hover:text-stone-600"
                    data-testid="insights-refresh"
                >
                    <RefreshCw className={`w-4 h-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
                </Button>
            </div>

            <div className="p-5 space-y-6">
                
                {/* Patterns */}
                {data.patterns.length > 0 && (
                     <div data-testid="insights-patterns">
                        <h4 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                             <Target className="w-3 h-3" /> Identified Patterns
                        </h4>
                        <div className="grid gap-3">
                            {data.patterns.map((p, i) => (
                                <div key={i} className="bg-white p-3 rounded-lg border border-stone-100 shadow-sm">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-semibold text-stone-700">{p.title}</span>
                                        {p.confidence > 0.8 && (
                                            <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded font-medium">High Confidence</span>
                                        )}
                                    </div>
                                    <div className="text-sm text-stone-600 space-y-1">
                                        {p.evidence.map((e, j) => (
                                            <p key={j} className="flex items-start gap-2">
                                                <span className="mt-1.5 w-1 h-1 bg-stone-300 rounded-full shrink-0" />
                                                {e}
                                            </p>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Playbook */}
                {data.playbook.length > 0 && (
                    <div data-testid="insights-playbook">
                         <h4 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                             <BookOpen className="w-3 h-3" /> Playbook
                        </h4>
                        <div className="space-y-3">
                            {data.playbook.map((item, i) => (
                                <div key={i} className="flex gap-4 p-3 bg-amber-50/50 rounded-lg border border-amber-100/50">
                                    <div className="shrink-0 mt-0.5">
                                        <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center text-amber-600 text-xs font-bold">
                                            {i + 1}
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <p className="font-medium text-stone-800 text-sm">
                                            When <span className="text-amber-700">{item.when}</span>...
                                        </p>
                                        <div className="grid grid-cols-2 gap-4 text-xs">
                                            <div className="text-green-700">
                                                <span className="font-bold uppercase opacity-70 block mb-1">Do</span>
                                                <ul className="list-disc pl-3 marker:text-green-400">
                                                    {item.do.map((d, j) => <li key={j}>{d}</li>)}
                                                </ul>
                                            </div>
                                            <div className="text-red-700">
                                                <span className="font-bold uppercase opacity-70 block mb-1">Avoid</span>
                                                <ul className="list-disc pl-3 marker:text-red-400">
                                                    {item.avoid.map((a, j) => <li key={j}>{a}</li>)}
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Next Focus */}
                {data.next_focus.length > 0 && (
                    <div>
                        <h4 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                             <Lightbulb className="w-3 h-3" /> Next Focus
                        </h4>
                        <div className="space-y-2">
                             {data.next_focus.map((f, i) => (
                                 <div key={i} className="flex items-start gap-3 p-3 bg-stone-900 text-stone-100 rounded-lg shadow-md">
                                     <Target className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
                                     <div>
                                         <p className="font-bold text-sm mb-0.5">{f.goal}</p>
                                         <p className="text-xs text-stone-400 mb-2">{f.why}</p>
                                         <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-stone-800 rounded text-xs text-amber-200">
                                             <span>action:</span>
                                             <span className="font-medium text-white">{f.action}</span>
                                         </div>
                                     </div>
                                 </div>
                             ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
