
"use client";

import React, { useState } from "react";
import { Plus, Search, AlertCircle, Trash2, Edit2, X, RefreshCw, CalendarPlus, UtensilsCrossed, Loader2, Check } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { usePantryList, useCreatePantryItem, useDeletePantryItem, useUpdatePantryItem, pantryKeys } from "@/features/pantry/hooks";
import { useRecipes } from "@/features/recipes/hooks";
import { useCurrentPlan, useUpdateEntry } from "@/features/plan/hooks";
import * as SheetPrimitive from "@radix-ui/react-dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CreatePantryItem, PantryItem, UpdatePantryItem } from "@/lib/api";
import { cn } from "@/lib/cn";
import { format, parseISO, startOfWeek, addDays as addDaysFn } from 'date-fns';
import { useToast } from "@/hooks/use-toast";


// --- Date Helpers (No date-fns) ---
function addDays(date: Date, days: number): Date {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
}

function formatDate(dateStr: string | undefined): string {
    if (!dateStr) return "";
    // Parse "YYYY-MM-DD" as local date components to prevent timezone shifts
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function getNextWeekISO(): string {
    const d = addDays(new Date(), 7);
    return d.toISOString().split("T")[0];
}

// --- Page Component ---

export default function PantryPage() {
    const [search, setSearch] = useState("");
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<PantryItem | null>(null);
    const [addToPlanItem, setAddToPlanItem] = useState<PantryItem | null>(null);
    const [addedItems, setAddedItems] = useState<Set<string>>(new Set());
    const queryClient = useQueryClient();

    // Queries
    const { data: allItems, isLoading } = usePantryList({ search });
    const { data: useSoonItems } = usePantryList({ useSoon: true });

    const { mutate: deleteItem } = useDeletePantryItem();

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 pb-20">
            <div className="max-w-4xl mx-auto p-4 sm:p-6 space-y-8">

                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Pantry</h1>
                        <p className="text-slate-500 text-sm">Manage your inventory</p>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" size="icon" onClick={() => queryClient.invalidateQueries({ queryKey: pantryKeys.all })}>
                            <RefreshCw className="w-4 h-4" />
                        </Button>
                        <Button onClick={() => setIsAddOpen(true)}>
                            <Plus className="w-4 h-4 mr-2" />
                            Add Item
                        </Button>
                    </div>
                </div>

                {/* Use Soon Carousel */}
                {useSoonItems && (
                    <section data-testid="pantry-use-soon-section">
                        <div className="flex items-center gap-2 mb-3 text-amber-600 dark:text-amber-500 font-semibold">
                            <AlertCircle className="w-5 h-5" />
                            Use Soon
                        </div>
                        {useSoonItems.length === 0 ? (
                            <div className="text-sm text-slate-500 italic p-6 text-center bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-dashed border-slate-200 dark:border-slate-800">
                                No expiring items in the next 5 days.
                            </div>
                        ) : (
                            <div className="flex gap-4 overflow-x-auto pb-4 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide">
                                {useSoonItems.map((item) => (
                                    <Card key={item.id} className="min-w-[200px] border-amber-200 bg-amber-50 dark:bg-amber-900/10 dark:border-amber-900/50">
                                        <CardContent className="p-3">
                                            <div className="font-medium truncate">{item.name}</div>
                                            <div className="text-xs text-amber-700 dark:text-amber-400 mt-1 mb-2">
                                                Expires {formatDate(item.expires_on)}
                                            </div>
                                            <div className="flex gap-2">
                                                <Button 
                                                    size="sm" 
                                                    variant={addedItems.has(item.id) ? "default" : "outline"}
                                                    disabled={addedItems.has(item.id)}
                                                    className={cn(
                                                        "w-full h-7 text-xs transition-all duration-300",
                                                        addedItems.has(item.id) 
                                                            ? "bg-green-600 hover:bg-green-700 text-white border-transparent"
                                                            : "border-amber-300 text-amber-800 hover:bg-amber-100 dark:border-amber-800 dark:text-amber-300 dark:hover:bg-amber-900/30"
                                                    )}
                                                    onClick={() => setAddToPlanItem(item)}
                                                    data-testid={`use-soon-add-to-plan-${item.id}`}
                                                >
                                                    {addedItems.has(item.id) ? (
                                                        <><Check className="w-3 h-3 mr-1" /> Plan Added</>
                                                    ) : (
                                                        <><CalendarPlus className="w-3 h-3 mr-1" /> Add to Plan</>
                                                    )}
                                                </Button>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </section>
                )}

                {/* Inventory List */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 sticky top-0 bg-slate-50 dark:bg-slate-950 py-2 z-10">
                        <div className="relative flex-1">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
                            <Input
                                type="search"
                                placeholder="Search pantry..."
                                className="pl-9 bg-white dark:bg-slate-900"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="text-center py-10 text-slate-500">Loading inventory...</div>
                    ) : allItems?.length === 0 ? (
                        <div className="text-center py-10 text-slate-500 border-2 border-dashed rounded-lg">
                            No items found. Add something to your pantry!
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {allItems?.map((item) => (
                                <Card key={item.id} className="group">
                                    <CardContent className="p-3 flex justify-between items-start">
                                        <div>
                                            <div className="font-medium">{item.name}</div>
                                            <div className="text-sm text-slate-500">
                                                {item.qty ? `${item.qty} ${item.unit || ''}` : 'No quantity'}
                                                {item.category && <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{item.category}</span>}
                                            </div>
                                            {item.expires_on && (
                                                <div className="text-xs text-slate-400 mt-1">
                                                    Exp: {formatDate(item.expires_on)}
                                                </div>
                                            )}
                                        </div>
                                        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-blue-500" onClick={() => setEditingItem(item)}>
                                                <Edit2 className="w-4 h-4" />
                                            </Button>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-red-500" onClick={() => deleteItem(item.id)}>
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </section>
            </div>

            {/* Quick Add Modal */}
            {isAddOpen && <QuickAddModal onClose={() => setIsAddOpen(false)} />}
            
            {/* Edit Modal */}
            {editingItem && (
                <EditItemModal 
                    item={editingItem} 
                    onClose={() => setEditingItem(null)} 
                />
            )}

            {/* Add To Plan Sheet */}
            {addToPlanItem && (
                <AddToPlanSheet
                    item={addToPlanItem}
                    onClose={() => setAddToPlanItem(null)}
                    onSuccess={() => {
                        setAddedItems(new Set(addedItems).add(addToPlanItem.id));
                    }}
                />
            )}
        </div>
    );
}

function AddToPlanSheet({ item, onClose, onSuccess }: { item: PantryItem; onClose: () => void; onSuccess?: () => void }) {
    const { plan } = useCurrentPlan();
    const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState(item.name); // Prefill with item name
    const { data: recipes, isLoading: isRecipesLoading } = useRecipes({ search: searchTerm });
    const { updateEntry, isUpdating } = useUpdateEntry();
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Prepare plan slots (Next 7 days if no active plan, or current plan entries)
    // For MVP, rely on useCurrentPlan. If no plan, we can't add. User needs to generate one.
    // Ideally we should auto-generate or show "Create Plan First".
    // Assuming plan exists for v3.2.

    const handleSelectRecipe = (recipe: any) => {
        if (!selectedEntryId) {
             toast({ title: "Select a slot", description: "Please choose which meal to replace.", variant: "destructive" });
             return;
        }

        updateEntry(selectedEntryId, { recipe_id: recipe.id })
            .then(() => {
                queryClient.invalidateQueries({ queryKey: ["plan"] }); // Force plan refresh
                queryClient.invalidateQueries({ queryKey: ["grocery"] });
                if (onSuccess) onSuccess();
                
                toast({ 
                    title: "Added to Plan", 
                    description: `Success! ${recipe.title} is now scheduled.`,
                    className: "bg-green-600 text-white border-green-700 dark:bg-green-600 dark:text-white"
                });
                onClose();
            })
            .catch(() => {
                toast({ title: "Error", description: "Failed to update plan.", variant: "destructive" });
            });
    };

    const sortedEntries = plan?.entries
        .sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime()) || [];

    return (
        <Sheet open={true} onOpenChange={(open) => !open && onClose()}>
            <SheetContent className="w-full sm:max-w-md overflow-y-auto">
                <SheetHeader className="mb-4">
                    <SheetTitle>Add {item.name} to Plan</SheetTitle>
                    <SheetDescription>
                        Find a recipe using {item.name} and swap it into your weekly schedule.
                    </SheetDescription>
                </SheetHeader>

                <div className="space-y-6">
                    {/* 1. Select Slot */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">1. Choose a slot to replace</label>
                        {!plan ? (
                            <div className="p-4 bg-slate-100 rounded text-sm text-slate-500 text-center">
                                No active plan found. Please generate a week plan first.
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto border rounded-md p-2">
                                {sortedEntries.map((entry: any) => {
                                    const dateObj = new Date(entry.date);
                                    const isSelected = selectedEntryId === entry.id;
                                    const isPast = dateObj < new Date(new Date().setHours(0,0,0,0));
                                    
                                    if(isPast) return null; // Don't allow planning in past

                                    return (
                                        <div 
                                            key={entry.id}
                                            onClick={() => setSelectedEntryId(entry.id)}
                                            className={cn(
                                                "flex items-center justify-between p-2 rounded cursor-pointer border transition-colors text-sm",
                                                isSelected ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-transparent hover:bg-slate-50 dark:hover:bg-slate-800"
                                            )}
                                        >
                                            <div className="flex flex-col">
                                                <span className="font-medium">
                                                    {format(dateObj, 'EEE')} {entry.meal_type === 'lunch' ? 'Lunch' : 'Dinner'}
                                                </span>
                                                <span className="text-xs text-slate-500 truncate max-w-[200px]">
                                                    {entry.recipe_title || (entry.is_leftover ? "Leftovers" : "Empty")}
                                                </span>
                                            </div>
                                            {isSelected && <Check className="w-4 h-4 text-blue-500" />}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* 2. Select Recipe */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium">2. Find a recipe</label>
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
                            <Input 
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Search recipes..."
                                className="pl-9"
                            />
                        </div>
                        
                        <div className="space-y-2 mt-2">
                            {isRecipesLoading ? (
                                <div className="text-center py-4 text-slate-500">
                                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                                    Searching...
                                </div>
                            ) : recipes?.length === 0 ? (
                                <div className="text-center py-4 text-slate-500 text-sm">
                                    No recipes found for "{searchTerm}".
                                </div>
                            ) : (
                                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                                    {recipes?.map((recipe) => (
                                        <div 
                                            key={recipe.id}
                                            className="flex items-center gap-3 p-2 rounded-lg border hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer group"
                                            onClick={() => handleSelectRecipe(recipe)}
                                        >
                                             <div className="h-12 w-12 rounded-md bg-slate-200 flex-shrink-0 overflow-hidden">
                                                {recipe.primary_image_url ? (
                                                    <img src={recipe.primary_image_url} alt="" className="w-full h-full object-cover" />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center text-slate-400">
                                                        <UtensilsCrossed className="w-5 h-5" />
                                                    </div>
                                                )}
                                             </div>
                                             <div className="flex-1 min-w-0">
                                                 <div className="font-medium text-sm truncate">{recipe.title}</div>
                                                 <div className="text-xs text-slate-500 flex gap-2">
                                                     <span>{recipe.time_minutes || 30}m</span>
                                                     {/* Show match indicator if ingredient matches? */}
                                                 </div>
                                             </div>
                                             <Button 
                                                size="sm" 
                                                variant="ghost" 
                                                className="opacity-0 group-hover:opacity-100"
                                                disabled={!selectedEntryId || isUpdating}
                                            >
                                                Select
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}

function EditItemModal({ item, onClose }: { item: PantryItem; onClose: () => void }) {
    const { mutate, isPending } = useUpdatePantryItem();
    const [formData, setFormData] = useState<UpdatePantryItem>({
        name: item.name,
        qty: item.qty,
        unit: item.unit,
        category: item.category,
        expires_on: item.expires_on,
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        mutate({ id: item.id, data: formData }, {
            onSuccess: () => onClose()
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="p-4 border-b dark:border-slate-800 flex justify-between items-center">
                    <h3 className="font-semibold">Edit Item</h3>
                    <button onClick={onClose} className="text-slate-500 hover:text-slate-900">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-4 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Name</label>
                        <Input
                            autoFocus
                            value={formData.name || ""}
                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Qty</label>
                            <Input
                                type="number"
                                step="0.1"
                                value={formData.qty || ""}
                                onChange={e => setFormData({ ...formData, qty: e.target.value ? parseFloat(e.target.value) : undefined })}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Unit</label>
                            <Input
                                value={formData.unit || ""}
                                onChange={e => setFormData({ ...formData, unit: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Category</label>
                        <select
                            className="flex h-9 w-full rounded-md border border-slate-200 bg-transparent px-3 py-1 text-sm shadow-sm dark:border-slate-800"
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                        >
                            <option value="general">General</option>
                            <option value="produce">Produce</option>
                            <option value="dairy">Dairy</option>
                            <option value="protein">Protein</option>
                            <option value="pantry">Pantry</option>
                            <option value="frozen">Frozen</option>
                            <option value="spice">Spice</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Expires On</label>
                        <Input
                            type="date"
                            value={formData.expires_on || ""}
                            onChange={e => setFormData({ ...formData, expires_on: e.target.value || undefined })}
                        />
                    </div>

                    <div className="pt-2 flex justify-end gap-2">
                        <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                        <Button type="submit" disabled={isPending}>
                            {isPending ? "Saving..." : "Save Changes"}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}

function QuickAddModal({ onClose }: { onClose: () => void }) {
    const { mutate, isPending } = useCreatePantryItem();
    const [formData, setFormData] = useState<CreatePantryItem>({
        name: "",
        qty: undefined,
        unit: "",
        category: "general",
        source: "manual",
        expires_on: undefined
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.name) return;

        mutate(formData, {
            onSuccess: () => onClose()
        });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="p-4 border-b dark:border-slate-800 flex justify-between items-center">
                    <h3 className="font-semibold">Quick Add Item</h3>
                    <button onClick={onClose} className="text-slate-500 hover:text-slate-900"><X className="w-5 h-5" /></button>
                </div>

                <form onSubmit={handleSubmit} className="p-4 space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Name</label>
                        <Input
                            autoFocus
                            value={formData.name}
                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                            placeholder="e.g. Milk, Rice"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Qty</label>
                            <Input
                                type="number"
                                step="0.1"
                                value={formData.qty || ""}
                                onChange={e => setFormData({ ...formData, qty: e.target.value ? parseFloat(e.target.value) : undefined })}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Unit</label>
                            <Input
                                value={formData.unit || ""}
                                onChange={e => setFormData({ ...formData, unit: e.target.value })}
                                placeholder="pcs, kg"
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Category</label>
                        <select
                            className="flex h-9 w-full rounded-md border border-slate-200 bg-transparent px-3 py-1 text-sm shadow-sm dark:border-slate-800"
                            value={formData.category}
                            onChange={e => setFormData({ ...formData, category: e.target.value })}
                        >
                            <option value="general">General</option>
                            <option value="produce">Produce</option>
                            <option value="dairy">Dairy</option>
                            <option value="protein">Protein</option>
                            <option value="pantry">Pantry</option>
                            <option value="frozen">Frozen</option>
                            <option value="spice">Spice</option>
                        </select>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Expires On</label>
                        <Input
                            type="date"
                            value={formData.expires_on || ""}
                            onChange={e => setFormData({ ...formData, expires_on: e.target.value || undefined })}
                        />
                    </div>

                    <div className="pt-2 flex justify-end gap-2">
                        <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                        <Button type="submit" disabled={isPending || !formData.name}>
                            {isPending ? "Adding..." : "Add to Pantry"}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
