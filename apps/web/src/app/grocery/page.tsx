
"use client";

import React, { useState } from "react";
import { Check, Plus, RefreshCw, ShoppingCart, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { useCurrentGrocery, useGenerateGrocery, useUpdateGroceryItem, groceryKeys } from "@/features/grocery/hooks";
import { useRecipes } from "@/features/recipes/hooks";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/cn";

export default function GroceryPage() {
    const { data: groceryList, isLoading, isError } = useCurrentGrocery();
    const queryClient = useQueryClient();

    if (isLoading) return <div className="p-8 text-center text-slate-500">Loading grocery list...</div>;

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 pb-20">
            <div className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Grocery List</h1>
                        <p className="text-slate-500 text-sm">
                            {groceryList ? `Created ${new Date(groceryList.created_at).toLocaleDateString()}` : "No active list"}
                        </p>
                    </div>
                    {groceryList && (
                        <Button variant="outline" size="sm" onClick={() => queryClient.invalidateQueries({ queryKey: groceryKeys.current() })}>
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Refresh
                        </Button>
                    )}
                </div>

                {!groceryList || isError ? (
                    <GenerateListSection />
                ) : (
                    <ActiveListSection list={groceryList} />
                )}
            </div>
        </div>
    );
}

// ... imports
import { useCurrentPlan } from "@/features/plan/hooks";

// ... existing code

function GenerateListSection() {
    const { data: recipes } = useRecipes();
    const { data: plan } = useCurrentPlan();
    const { mutate: generate, isPending } = useGenerateGrocery();
    const [selectedIds, setSelectedIds] = useState<string[]>([]);

    const toggleRecipe = (id: string) => {
        setSelectedIds(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const handleGenerate = () => {
        generate({ recipeIds: selectedIds });
    };

    const handleGenerateFromPlan = () => {
        if (plan) {
            generate({ planId: plan.id });
        }
    };

    return (
        <Card>
            <CardContent className="p-6 space-y-6">
                <div className="text-center space-y-2">
                    <div className="bg-slate-100 dark:bg-slate-800 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
                        <ShoppingCart className="w-6 h-6 text-slate-500" />
                    </div>
                    <h3 className="text-lg font-semibold">Start a new list</h3>
                    <p className="text-slate-500 text-sm">Select recipes or use your weekly plan.</p>
                </div>

                {/* Plan CTA */}
                {plan && !plan.entries.every(e => !e.recipe_id) && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg p-4 flex items-center justify-between">
                        <div>
                            <div className="font-medium text-blue-900 dark:text-blue-100">Weekly Plan Available</div>
                            <div className="text-xs text-blue-700 dark:text-blue-300">
                                {plan.entries.filter(e => e.recipe_id).length} meals planned
                            </div>
                        </div>
                        <Button size="sm" onClick={handleGenerateFromPlan} disabled={isPending}>
                            Use Weekly Plan
                        </Button>
                    </div>
                )}

                {plan && <div className="text-center text-xs text-slate-400 font-medium my-2">- OR -</div>}

                <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm font-medium text-slate-900 dark:text-slate-200">
                        <span>Select Recipes ({selectedIds.length})</span>
                        {recipes && (
                            <button
                                onClick={() => setSelectedIds(selectedIds.length === recipes.length ? [] : recipes.map(r => r.id))}
                                className="text-blue-500 hover:underline text-xs"
                            >
                                {selectedIds.length === recipes.length ? "Deselect All" : "Select All"}
                            </button>
                        )}
                    </div>

                    <div className="border rounded-md divide-y max-h-60 overflow-y-auto">
                        {recipes?.map(recipe => (
                            <div
                                key={recipe.id}
                                className={cn(
                                    "p-3 flex items-center gap-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors",
                                    selectedIds.includes(recipe.id) && "bg-blue-50 dark:bg-blue-900/10"
                                )}
                                onClick={() => toggleRecipe(recipe.id)}
                            >
                                <div className={cn(
                                    "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                                    selectedIds.includes(recipe.id) ? "bg-blue-500 border-blue-500 text-white" : "border-slate-300"
                                )}>
                                    {selectedIds.includes(recipe.id) && <Check className="w-3 h-3" />}
                                </div>
                                <span className="text-sm truncate font-medium">{recipe.title}</span>
                            </div>
                        ))}
                        {(!recipes || recipes.length === 0) && (
                            <div className="p-4 text-center text-sm text-slate-500 font-italic">
                                No recipes found. Seed data first?
                            </div>
                        )}
                    </div>
                </div>

                <Button className="w-full" size="lg" onClick={handleGenerate} disabled={selectedIds.length === 0 || isPending}>
                    {isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                    Generate Manual List
                </Button>
            </CardContent>
        </Card>
    );
}

function ActiveListSection({ list }: { list: any }) {
    // Sort items: Need -> Purchased -> Have
    // Logic: 
    // - Need: status === 'need'
    // - Purchased: status === 'purchased'
    // - Have: status === 'have' (Collapsed)

    const items = list.items || [];
    const needItems = items.filter((i: any) => i.status === 'need');
    const purchasedItems = items.filter((i: any) => i.status === 'purchased');
    const haveItems = items.filter((i: any) => i.status === 'have');

    const { mutate: updateItem } = useUpdateGroceryItem();

    const toggleStatus = (item: any) => {
        const newStatus = item.status === 'need' ? 'purchased' : 'need';
        updateItem({ id: item.id, data: { status: newStatus } });
    };

    return (
        <div className="space-y-6">
            {/* Need Section */}
            <section className="space-y-3">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    To Buy <Badge variant="secondary" className="rounded-full px-2">{needItems.length}</Badge>
                </h3>
                {needItems.length === 0 && purchasedItems.length === 0 && (
                    <p className="text-sm text-slate-500 italic">Nothing to buy!</p>
                )}
                <div className="bg-white dark:bg-slate-900 rounded-lg shadow-sm border overflow-hidden divide-y dark:divide-slate-800">
                    {needItems.map((item: any) => (
                        <GroceryItemRow key={item.id} item={item} onToggle={() => toggleStatus(item)} />
                    ))}
                </div>
            </section>

            {/* Purchased Section */}
            {purchasedItems.length > 0 && (
                <section className="space-y-3 opacity-60">
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Purchased</h3>
                    <div className="bg-white dark:bg-slate-900 rounded-lg shadow-sm border overflow-hidden divide-y dark:divide-slate-800">
                        {purchasedItems.map((item: any) => (
                            <GroceryItemRow key={item.id} item={item} onToggle={() => toggleStatus(item)} />
                        ))}
                    </div>
                </section>
            )}

            {/* Have Section */}
            {haveItems.length > 0 && (
                <section className="space-y-3 pt-4 border-t">
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm flex items-center gap-2">
                        Already Have <Badge variant="outline" className="rounded-full px-2">{haveItems.length}</Badge>
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {haveItems.map((item: any) => (
                            <div key={item.id} className="text-sm p-2 bg-slate-100 dark:bg-slate-800 rounded flex justify-between text-slate-500">
                                <span className="truncate">{item.name}</span>
                                <span className="text-xs">{item.reason?.replace('Pantry match: ', '')}</span>
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
}

function GroceryItemRow({ item, onToggle }: { item: any, onToggle: () => void }) {
    const isPurchased = item.status === 'purchased';
    return (
        <div
            className={cn(
                "p-3 flex items-center gap-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors",
                isPurchased && "bg-slate-50"
            )}
            onClick={onToggle}
        >
            <div className={cn(
                "w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors",
                isPurchased ? "bg-green-500 border-green-500 text-white" : "border-slate-300"
            )}>
                {isPurchased && <Check className="w-3 h-3" />}
            </div>
            <div className="flex-1 min-w-0">
                <div className={cn("font-medium truncate", isPurchased && "line-through text-slate-400")}>
                    {item.name}
                </div>
                <div className="text-xs text-slate-500">
                    {item.qty} {item.unit} {item.category && <span className="ml-1 opacity-70">• {item.category}</span>}
                </div>
            </div>
        </div>
    )
}
