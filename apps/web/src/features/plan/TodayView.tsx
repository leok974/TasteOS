
"use client";

import { useCurrentPlan } from "./hooks";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { ArrowRight, ChefHat, RefreshCw } from "lucide-react";

export function TodayView() {
    const { plan, isLoading, isEmpty } = useCurrentPlan();

    if (isLoading) return <TodaySkeleton />;
    if (!plan || isEmpty) return <EmptyTodayState />;

    const todayStr = format(new Date(), 'yyyy-MM-dd');
    const lunch = plan.entries.find(e => e.date === todayStr && e.meal_type === 'lunch');
    const dinner = plan.entries.find(e => e.date === todayStr && e.meal_type === 'dinner');

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Today's Menu</h2>
                    <p className="text-muted-foreground">{format(new Date(), 'EEEE, MMMM do')}</p>
                </div>
                <Link href="/plan">
                    <Button variant="ghost" className="gap-2">
                        View Full Week <ArrowRight className="w-4 h-4" />
                    </Button>
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <MealCard type="Lunch" entry={lunch} />
                <MealCard type="Dinner" entry={dinner} />
            </div>
        </div>
    );
}

function MealCard({ type, entry }: { type: string, entry?: any }) {
    if (!entry) {
        return (
            <Card className="h-full border-dashed">
                <CardHeader>
                    <CardTitle className="text-lg text-muted-foreground">{type}</CardTitle>
                </CardHeader>
                <CardContent className="h-32 flex items-center justify-center text-muted-foreground text-sm">
                    Nothing planned
                </CardContent>
            </Card>
        );
    }

    const isLeftover = entry.is_leftover;

    return (
        <Card className="h-full overflow-hidden flex flex-col hover:shadow-md transition-shadow">
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
                <div className="space-y-1">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{type}</span>
                    <CardTitle className="text-xl">
                        {entry.recipe_id ? (
                            <Link href={`/recipes/${entry.recipe_id}`} className="hover:underline decoration-primary/50 underline-offset-4">
                                {entry.recipe_title}
                            </Link>
                        ) : (
                            isLeftover ? "Leftovers" : "No Recipe"
                        )}
                    </CardTitle>
                </div>
                {isLeftover ? (
                    <Badge variant="secondary" className="gap-1"><RefreshCw className="w-3 h-3" /> Leftover</Badge>
                ) : (
                    <Badge variant="outline" className="gap-1"><ChefHat className="w-3 h-3" /> Fresh</Badge>
                )}
            </CardHeader>

            <CardContent className="flex-1 flex flex-col justify-end gap-4">
                {/* Method Pill */}
                {entry.method_choice && !isLeftover && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className="font-medium text-foreground">{entry.method_choice}</span>
                        {entry.method_options_json?.["Stove"]?.time && (
                            <span>• {entry.method_options_json["Stove"].time}</span>
                        )}
                    </div>
                )}

                {entry.recipe_id && (
                    <Link href={`/recipes/${entry.recipe_id}`} className="w-full">
                        <Button className="w-full" variant={isLeftover ? "secondary" : "default"}>
                            {isLeftover ? "View Original Recipe" : "Start Cook Mode"}
                        </Button>
                    </Link>
                )}
            </CardContent>
        </Card>
    );
}

function TodaySkeleton() {
    return (
        <div className="space-y-6">
            <div className="flex justify-between">
                <Skeleton className="h-8 w-40" />
                <Skeleton className="h-8 w-24" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Skeleton className="h-48 w-full rounded-xl" />
                <Skeleton className="h-48 w-full rounded-xl" />
            </div>
        </div>
    )
}

function EmptyTodayState() {
    return (
        <div className="rounded-xl border bg-card text-card-foreground shadow-sm p-8 text-center space-y-4">
            <div className="bg-muted w-12 h-12 rounded-full flex items-center justify-center mx-auto">
                <ChefHat className="w-6 h-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold">No Plan Active</h3>
            <p className="text-muted-foreground">Generate a weekly plan to see today's meals here.</p>
            <Link href="/plan">
                <Button>Go to Planner</Button>
            </Link>
        </div>
    )
}
