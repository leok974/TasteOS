
"use client";

import React, { useState } from "react";
import { Plus, Search, AlertCircle, Trash2, Edit2, X, RefreshCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { usePantryList, useCreatePantryItem, useDeletePantryItem, useUpdatePantryItem, pantryKeys } from "@/features/pantry/hooks";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CreatePantryItem, PantryItem, UpdatePantryItem } from "@/lib/api";

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
                                    <Card key={item.id} className="min-w-[160px] border-amber-200 bg-amber-50 dark:bg-amber-900/10 dark:border-amber-900/50">
                                        <CardContent className="p-3">
                                            <div className="font-medium truncate">{item.name}</div>
                                            <div className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                                                Expires {formatDate(item.expires_on)}
                                            </div>
                                            {item.qty && (
                                                <div className="text-sm font-semibold mt-2">
                                                    {item.qty} {item.unit}
                                                </div>
                                            )}
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
        </div>
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
