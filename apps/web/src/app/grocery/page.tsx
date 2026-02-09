
"use client";

import React, { useState } from "react";
import { Check, Plus, RefreshCw, ShoppingCart, Loader2, X, Undo, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { useCurrentGrocery, useGenerateGrocery, useUpdateGroceryItem, groceryKeys, useClearGrocery } from "@/features/grocery/hooks";
import { useRecipes } from "@/features/recipes/hooks";
import { useCurrentPlan } from "@/features/plan/hooks";
import { useToast } from "@/hooks/use-toast";
import { ToastAction } from "@/components/ui/toast";
import { deletePantryItem } from "@/lib/api";
import { pantryKeys } from "@/features/pantry/hooks";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
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
import { cn } from "@/lib/cn";

import { useRecipe } from "@/features/recipes/hooks";

export default function GroceryPage() {
    const { data: groceryList, isLoading, isError, isRefetching } = useCurrentGrocery();
    const { plan } = useCurrentPlan();
    const { mutate: generate, isPending: isGenerating } = useGenerateGrocery();
    const { mutate: clearList, isPending: isClearing } = useClearGrocery();
    const queryClient = useQueryClient();
    const [isClearDialogOpen, setIsClearDialogOpen] = useState(false);

    const isStale = false; // Disable complex stale logic for V2

    const handleGenerateFromPlan = () => {
        // Legacy or refresh? 
        // For V2, we might want a different logic or button
    };
    
    // Handler for ephemeral overrides (Legacy)
    const handleIncludeEntry = (entryId: string) => {
        if (!plan) return;
        
        // We need to re-generate the list, effectively passing ALL current excluded IDs + this one?
        // OR does backend handle "additive" overriding?
        // Loop v2.1 Backend: request.include_entry_ids are IDs to IGNORE checking leftovers for.
        // It does NOT persist state. It is ephemeral for the generation call.
        // So we need to re-generate with planId AND include_entry_ids=[entryId].
        // If there are other entries we previously included, we lose them unless we track state locally.
        // BUT for MVP/Prototype, maybe just re-generating with this one entry ID is enough to demonstrate "Override".
        // A better UX would be to accumulate overrides.
        // Let's assume for now the user clicks one at a time.
        // Wait, if I click one, it regenerates. The other skipped items will still be skipped (returned in meta).
        // Then I can click another one.
        // The problem is subsequent calls need to include the PREVIOUSLY included IDs too, otherwise they will disappear from the list (get skipped again).
        // So I need state: `overriddenEntryIds` in the parent component.
        // BUT the grocery list response does not tell us which IDs were overridden in the PAST, only which were skipped NOW.
        // Actually, if an item is NOT skipped, it is just in the list.
        // So I can't easily distinguish "included because override" vs "included because needed".
        // Unless I persist `overriddenEntryIds` in local state.
        
        // Let's implement local state for overrides.
        generate({ 
            planId: plan.id,
            includeEntryIds: [...overrides, entryId]
        }, {
             onSuccess: () => {
                 setOverrides(prev => [...prev, entryId]);
                 setConfirmIncludeState(null);
             }
        });
    };
    
    // State to track overrides across re-generations
    const [overrides, setOverrides] = useState<string[]>([]);
    const [confirmIncludeState, setConfirmIncludeState] = useState<{ entryId: string, recipeId: string } | null>(null);

    if (isLoading) return <div className="p-8 text-center text-slate-500">Loading grocery list...</div>;

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 pb-20">
            <div className="max-w-2xl mx-auto p-4 sm:p-6 space-y-6">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Grocery List</h1>
                        <p className="text-slate-500 text-sm">
                           {/* Debug Marker */}
                           <span className="text-xs bg-slate-100 rounded px-1 mr-2">v2</span>
                            {groceryList ? `Created ${new Date(groceryList.created_at).toLocaleDateString()}` : "No active list"}
                        </p>
                    </div>
                     <div className="flex gap-2">
                        {/* Sync Button */}
                        {groceryList && plan && (
                            <Button 
                                variant={isStale ? "default" : "outline"} 
                                size="sm" 
                                onClick={() => {
                                    setOverrides([]); // Reset overrides on fresh sync?
                                    handleGenerateFromPlan();
                                }}
                                disabled={isGenerating}
                                className="min-w-[120px]"
                            >
                                <RefreshCw className={cn("w-4 h-4 mr-2", isGenerating && "animate-spin")} />
                                {isGenerating ? "Syncing..." : (isStale ? "Sync to Plan" : "Regenerate")}
                            </Button>
                        )}
                        
                        {/* Clear / Start Over */}
                        {groceryList && (
                             <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-9 w-9 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/10"
                                title="Start Over (Delete List)"
                                onClick={() => setIsClearDialogOpen(true)}
                                disabled={isClearing || isGenerating}
                            >
                                <Trash2 className="w-4 h-4" />
                            </Button>
                        )}
                        
                        {/* Standard Refresh (if no plan, or just purely refreshing data) */}
                        {groceryList && !plan && (
                            <Button variant="outline" size="sm" 
                                onClick={() => {
                                    queryClient.invalidateQueries({ queryKey: groceryKeys.all });
                                }}
                                disabled={isRefetching}
                                className="min-w-[100px]"
                            >
                                <RefreshCw className={cn("w-4 h-4 mr-2", isRefetching && "animate-spin")} />
                                {isRefetching ? "Loading..." : "Refresh"}
                            </Button>
                        )}
                    </div>
                </div>

                <AlertDialog open={isClearDialogOpen} onOpenChange={setIsClearDialogOpen}>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Start Over?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This will delete your current grocery list. This action cannot be undone.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction 
                                onClick={() => {
                                    clearList();
                                    setIsClearDialogOpen(false);
                                }}
                                className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
                            >
                                {isClearing ? "Deleting..." : "Delete List"}
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>

                {!groceryList || isError ? (
                    <GenerateListSection />
                ) : (
                    <ActiveListSection 
                        list={groceryList} 
                        onInclude={(entryId, recipeId) => setConfirmIncludeState({ entryId, recipeId })}
                        isGenerating={isGenerating}
                    />
                )}
                
                {confirmIncludeState && (
                    <ConfirmIncludeModal 
                        open={!!confirmIncludeState}
                        onOpenChange={(open) => !open && setConfirmIncludeState(null)}
                        entryId={confirmIncludeState.entryId}
                        recipeId={confirmIncludeState.recipeId}
                        isConfirming={isGenerating}
                        onConfirm={() => {
                            handleIncludeEntry(confirmIncludeState.entryId);
                            // Modal closes on success inside handleIncludeEntry
                        }}
                    />
                )}
            </div>
        </div>
    );
}

function GenerateListSection() {
    const { data: recipes } = useRecipes();
    const { plan } = useCurrentPlan();
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
        console.log("Generating grocery list from plan:", plan?.id);
        if (plan) {
            generate({ planId: plan.id }, {
              onError: (err) => console.error("Generate failed:", err)
            });
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

// --- Modals ---

function ConfirmIncludeModal({ open, onOpenChange, entryId, recipeId, onConfirm, isConfirming }: { 
    open: boolean, 
    onOpenChange: (open: boolean) => void, 
    entryId: string, 
    recipeId: string,
    onConfirm: () => void,
    isConfirming?: boolean
}) {
    const { data: recipe, isLoading } = useRecipe(recipeId);

    return (
        <Dialog open={open} onOpenChange={(val) => !isConfirming && onOpenChange(val)}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Include Excluded Meal?</DialogTitle>
                    <DialogDescription>
                        Adding this meal back to the plan will add the following ingredients to your grocery list.
                    </DialogDescription>
                </DialogHeader>
                
                <div className="py-4">
                    <h4 className="text-sm font-medium mb-2 text-slate-900 dark:text-slate-100">
                        {isLoading ? "Loading recipe details..." : recipe?.title}
                    </h4>
                    
                    {isLoading ? (
                         <div className="flex items-center justify-center py-4">
                            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                        </div>
                    ) : (
                        <div className="bg-slate-50 dark:bg-slate-900 rounded p-3 text-sm max-h-[200px] overflow-y-auto">
                           {recipe?.ingredients?.length ? (
                               <ul className="space-y-1">
                                   {recipe.ingredients.map((ing: any, i: number) => (
                                       <li key={i} className="flex justify-between border-b last:border-0 border-slate-100 dark:border-slate-800 pb-1 last:pb-0">
                                           <span>{ing.name}</span>
                                           <span className="text-slate-500 text-xs">
                                               {ing.qty && `${ing.qty} ${ing.unit}`}
                                           </span>
                                       </li>
                                   ))}
                               </ul>
                           ) : (
                               <p className="text-slate-500 italic">No ingredients listed (or already pending).</p>
                           )}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isConfirming}>Cancel</Button>
                    <Button onClick={onConfirm} disabled={isLoading || isConfirming}>
                       {isConfirming && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                       Confirm Include
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

function ActiveListSection({ list, onInclude, isGenerating }: { list: any, onInclude?: (entryId: string, recipeId: string) => void, isGenerating?: boolean }) {
    // Sort items: Need -> Purchased -> Have
    // Logic: 
    // - Need: status === 'need'
    // - Purchased: status === 'purchased'
    // - Have: status === 'have' (Collapsed)
    
    // Toast setup (local for this page)
    const { toast, toasts, dismiss } = useToast();
    const queryClient = useQueryClient();

    const items = list.items || [];
    const needItems = items.filter((i: any) => i.status === 'need');
    const purchasedItems = items.filter((i: any) => i.status === 'purchased');
    const haveItems = items.filter((i: any) => i.status === 'have');

    const { mutate: updateItem } = useUpdateGroceryItem();

    const toggleStatus = (item: any) => {
        let newStatus = 'need';
        if (item.status === 'need') newStatus = 'purchased';
        else if (item.status === 'purchased') newStatus = 'need';
        else if (item.status === 'have') newStatus = 'need';
        
        updateItem({ id: item.id, data: { status: newStatus } }, {
            onSuccess: (data) => {
                // If moved to purchased, show toast with undo
                if (newStatus === 'purchased' && data.pantry_item_id) {
                     // Invalidate pantry to show up there immediately
                     queryClient.invalidateQueries({ queryKey: pantryKeys.all });
                     
                     toast({
                         title: "Moved to Pantry",
                         description: `Added ${data.name} to your pantry.`,
                         action: (
                             <ToastAction altText="Undo" onClick={() => handleUndo(data.pantry_item_id!, item.id, data.name)}>
                                 Undo
                             </ToastAction>
                         ),
                     });
                }
            }
        });
    };
    
    const handleUndo = async (pantryId: string, groceryId: string, name: string) => {
        try {
            await deletePantryItem(pantryId);
            // Revert grocery item to 'need'
            updateItem({ id: groceryId, data: { status: 'need' } });
            
            queryClient.invalidateQueries({ queryKey: pantryKeys.all });
            // dismiss();  // Don't modify all toasts
            toast({ title: "Undo Successful", description: `Removed ${name} from pantry.` });
        } catch (e) {
            console.error(e);
            toast({ title: "Undo Failed", description: "Could not remove item.", variant: "destructive" });
        }
    };

    return (
        <div className="space-y-6 relative">
             {/* Toast Container - Fixed or Absolute */}
             {toasts.length > 0 && (
                <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
                    {toasts.map((t) => (
                        <div key={t.id} className="bg-slate-900 text-white p-4 rounded-lg shadow-lg flex items-center gap-4 min-w-[300px] pointer-events-auto animate-in slide-in-from-bottom-2">
                            <div className="flex-1">
                                <h4 className="font-semibold text-sm">{t.title}</h4>
                                {t.description && <p className="text-xs opacity-80">{t.description}</p>}
                            </div>
                            {(t as any).action && (
                                <Button 
                                    variant="outline" 
                                    size="sm" 
                                    onClick={() => { (t as any).action.onClick(); dismiss(t.id); }}
                                    className="h-7 px-2 text-xs"
                                >
                                    <Undo className="w-3 h-3 mr-1" />
                                    {(t as any).action.label}
                                </Button>
                            )}
                            <button onClick={() => dismiss(t.id)} className="text-slate-400 hover:text-white">
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Excluded Meals Section */}
            {list.meta?.skipped_entries && list.meta.skipped_entries.length > 0 && (
                <section className="space-y-3 pt-4 border-t border-amber-200/50">
                     <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm flex items-center gap-2">
                        Excluded Meals <Badge variant="secondary" className="bg-amber-100 text-amber-800 hover:bg-amber-200">{list.meta?.skipped_entries?.length || 0}</Badge>
                    </h3>
                    <div className="space-y-2">
                        {list.meta.skipped_entries.map((skipped: any) => (
                            <div key={skipped.plan_entry_id} className="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 rounded-lg flex items-center justify-between text-sm">
                                <div>
                                    <span className="font-medium text-slate-900 dark:text-slate-100">{skipped.title}</span>
                                    <div className="flex items-center gap-2 mt-1">
                                         <Badge variant="outline" className="text-[10px] h-5 px-1 bg-white dark:bg-slate-900 text-slate-500 border-slate-200">
                                            Skips Grocery List
                                        </Badge>
                                        <span className="text-xs text-amber-700 dark:text-amber-400">
                                            Reason: {skipped.reason}
                                        </span>
                                    </div>
                                </div>
                                {onInclude && (
                                    <Button size="sm" variant="ghost" className="text-xs h-7 text-amber-900 hover:text-amber-950 hover:bg-amber-100 cursor-pointer"
                                        onClick={() => onInclude(skipped.plan_entry_id, skipped.recipe_id)}
                                        disabled={isGenerating}
                                    >
                                    {isGenerating ? "Updating..." : "Include anyway"}
                                    </Button>
                                )}
                            </div>
                        ))}
                    </div>
                </section>
            )}

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
                            <div 
                                key={item.id} 
                                onClick={() => toggleStatus(item)}
                                className="text-sm p-2 bg-slate-100 dark:bg-slate-800 rounded flex justify-between text-slate-500 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors group"
                            >
                                <div className="flex-1 min-w-0 pr-2">
                                     <span className={cn("truncate block group-hover:text-slate-900 dark:group-hover:text-slate-200")}>{item.name}</span>
                                     {item.expiry_days !== undefined && item.expiry_days !== null && (
                                         <span 
                                            data-testid={`grocery-expiry-chip-${item.id}`}
                                            className={cn(
                                                "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium mt-1",
                                                item.expiry_days <= 0 ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300" :
                                                item.expiry_days <= 2 ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300" :
                                                "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"
                                            )}
                                         >
                                            {item.expiry_days <= 0 ? "Expired" : `Expires in ${item.expiry_days} days`}
                                         </span>
                                     )}
                                </div>
                                <div className="flex items-center gap-2 self-start pt-0.5">
                                    <span className="text-xs">{item.reason?.replace('Pantry match: ', '')}</span>
                                    <Plus className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity text-blue-500" />
                                </div>
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
