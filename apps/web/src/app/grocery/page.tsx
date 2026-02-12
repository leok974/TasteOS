"use client";

import React, { useState, useEffect } from "react";
import { Plus, ShoppingCart, Trash2, Calendar, LayoutList, Loader2, MoreVertical, Search, ChefHat } from "lucide-react";
import { cn } from "@/lib/cn";
import { format } from "date-fns";
import { useRouter, useSearchParams } from "next/navigation";

// Hooks
import { 
    useGroceryLists, 
    useGroceryList, 
    useCreateGroceryList, 
    useGenerateGroceryList, 
    useDeleteGroceryList,
    useAddGroceryItem,
    useUpdateGroceryItem, 
    useDeleteGroceryItem,
    useUpdateGroceryList
} from "@/features/grocery/hooks";
import { useCurrentPlan } from "@/features/plan/hooks";
import { useRecipes } from "@/features/recipes/hooks";

// UI
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Checkbox } from "@/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function GroceryPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const listIdParam = searchParams.get("list");
    
    // Manage local selection state, sync with URL in effect
    const [selectedListId, setSelectedListId] = useState<string | null>(listIdParam);
    const [isMobileListOpen, setMobileListOpen] = useState(false);

    useEffect(() => {
        if (selectedListId && selectedListId !== listIdParam) {
            router.replace(`/grocery?list=${selectedListId}`);
        } else if (!selectedListId && listIdParam) {
            setSelectedListId(listIdParam);
        }
    }, [selectedListId, listIdParam, router]);

    return (
        <div className="flex h-[calc(100vh-4rem)] bg-background">
            {/* Sidebar (Desktop) */}
            <div className="hidden md:flex w-80 flex-col border-r bg-muted/10">
                <GrocerySidebar selectedId={selectedListId} onSelect={setSelectedListId} />
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0">
                 {/* Mobile Header / Toggle */}
                 <div className="md:hidden p-4 border-b flex items-center justify-between bg-card">
                     <h2 className="font-semibold">Grocery</h2>
                     <Button variant="outline" size="sm" onClick={() => setMobileListOpen(true)}>
                        <LayoutList className="w-4 h-4 mr-2"/> My Lists
                     </Button>
                 </div>
                 
                 {/* Mobile Sidebar Dialog */}
                 <Dialog open={isMobileListOpen} onOpenChange={setMobileListOpen}>
                    <DialogContent className="h-[80vh] p-0 gap-0 overflow-hidden flex flex-col">
                         <GrocerySidebar 
                            selectedId={selectedListId} 
                            onSelect={(id) => { setSelectedListId(id); setMobileListOpen(false); }} 
                         />
                    </DialogContent>
                 </Dialog>

                 {selectedListId ? (
                     <GroceryListDetail listId={selectedListId} />
                 ) : (
                     <EmptyState onSelectFirst={setSelectedListId} />
                 )}
            </div>
        </div>
    );
}

function EmptyState({ onSelectFirst }: { onSelectFirst: (id: string) => void }) {
    const { data } = useGroceryLists();
    
    useEffect(() => {
        if (data?.lists && data.lists.length > 0) {
            onSelectFirst(data.lists[0].id);
        }
    }, [data, onSelectFirst]);

    if (data?.lists && data.lists.length > 0) return (
         <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin text-muted-foreground mr-2" /> Redirecting...</div>
    );

    return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground">
            <ShoppingCart className="w-12 h-12 mb-4 opacity-20" />
            <h3 className="text-lg font-medium text-foreground">No lists yet</h3>
            <p className="mb-6">Create a list manually or generate one from your Weekly Plan.</p>
        </div>
    );
}

function GrocerySidebar({ selectedId, onSelect }: { selectedId: string | null, onSelect: (id: string) => void }) {
    const { data, isLoading } = useGroceryLists();
    const { mutate: createList, isPending: isCreating } = useCreateGroceryList();
    const { mutate: generateList, isPending: isGenerating } = useGenerateGroceryList();
    const { plan } = useCurrentPlan();
    const { data: recipesData } = useRecipes();
    
    // New List Dialog State
    const [isNewOpen, setIsNewOpen] = useState(false);
    const [newTitle, setNewTitle] = useState("");

    // Recipe Dialog State
    const [isRecipeOpen, setIsRecipeOpen] = useState(false);
    const [selectedRecipeIds, setSelectedRecipeIds] = useState<string[]>([]);
    const [recipeSearch, setRecipeSearch] = useState("");

    const handleCreate = () => {
        if (!newTitle.trim()) return;
        createList({ title: newTitle }, {
            onSuccess: (list) => {
                setIsNewOpen(false);
                setNewTitle("");
                onSelect(list.id);
            }
        });
    };

    const handleGenerateFromPlan = () => {
         if (!plan) return;
         const title = `Weekly Plan (${format(new Date(plan.week_start), "MMM d")})`;
         generateList({
             title,
             start: plan.week_start
         }, {
             onSuccess: (list) => onSelect(list.id)
         });
    };

    const handleGenerateFromRecipes = () => {
         if (selectedRecipeIds.length === 0) return;
         generateList({
             title: `Recipe List (${selectedRecipeIds.length})`,
             recipe_ids: selectedRecipeIds
         }, {
             onSuccess: (list) => {
                 setIsRecipeOpen(false);
                 setSelectedRecipeIds([]);
                 onSelect(list.id);
             }
         });
    };

    const filteredRecipes = recipesData?.filter(r => r.title.toLowerCase().includes(recipeSearch.toLowerCase())) || [];

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b space-y-2">
                 <Button className="w-full justify-start" onClick={() => setIsNewOpen(true)}>
                    <Plus className="w-4 h-4 mr-2" /> New Manual List
                 </Button>
                 {plan && (
                     <Button 
                        variant="secondary" 
                        className="w-full justify-start" 
                        onClick={handleGenerateFromPlan}
                        disabled={isGenerating}
                    >
                        <Calendar className="w-4 h-4 mr-2" /> 
                        {isGenerating ? "Generating..." : "From Weekly Plan"}
                     </Button>
                 )}
                 <Button 
                    variant="outline" 
                    className="w-full justify-start" 
                    onClick={() => setIsRecipeOpen(true)}
                    disabled={isGenerating}
                >
                    <ChefHat className="w-4 h-4 mr-2" /> From Selected Recipes
                </Button>
            </div>

            <ScrollArea className="flex-1">
                <div className="p-2 space-y-1">
                    {isLoading && <div className="p-4 text-sm text-center text-muted-foreground">Loading lists...</div>}
                    {data?.lists?.map(list => (
                        <button
                            key={list.id}
                            onClick={() => onSelect(list.id)}
                            className={cn(
                                "w-full flex flex-col items-start px-3 py-2 rounded-md transition-colors text-sm",
                                selectedId === list.id 
                                    ? "bg-primary/10 text-primary font-medium" 
                                    : "hover:bg-muted text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <span className="truncate w-full text-left">{list.title}</span>
                            <div className="flex items-center text-xs opacity-70 mt-1 w-full justify-between">
                                <span>{list.item_count} items</span>
                                <span>{format(new Date(list.created_at), "MMM d")}</span>
                            </div>
                        </button>
                    ))}
                </div>
            </ScrollArea>

            <Dialog open={isNewOpen} onOpenChange={setIsNewOpen}>
                <DialogContent>
                    <DialogHeader><DialogTitle>Create New List</DialogTitle></DialogHeader>
                    <Input 
                        placeholder="List Title (e.g. Costco Run)" 
                        value={newTitle} 
                        onChange={e => setNewTitle(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleCreate()}
                    />
                    <DialogFooter>
                        <Button onClick={handleCreate} disabled={isCreating || !newTitle.trim()}>
                            {isCreating ? "Creating..." : "Create"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={isRecipeOpen} onOpenChange={setIsRecipeOpen}>
                <DialogContent className="max-h-[80vh] flex flex-col">
                    <DialogHeader><DialogTitle>Select Recipes</DialogTitle></DialogHeader>
                    <div className="relative">
                        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input placeholder="Search recipes..." className="pl-8" value={recipeSearch} onChange={e => setRecipeSearch(e.target.value)} />
                    </div>
                    <ScrollArea className="flex-1 mt-2 border rounded-md p-2 min-h-[200px]">
                         {filteredRecipes.length === 0 ? (
                             <div className="text-center p-4 text-sm text-muted-foreground">No recipes found</div>
                         ) : (
                             filteredRecipes.map(recipe => (
                                 <div key={recipe.id} className="flex items-center space-x-2 py-2 px-1 hover:bg-muted/50 rounded">
                                     <Checkbox 
                                        id={`r-${recipe.id}`} 
                                        checked={selectedRecipeIds.includes(recipe.id)}
                                        onCheckedChange={(checked) => {
                                            if (checked) setSelectedRecipeIds([...selectedRecipeIds, recipe.id]);
                                            else setSelectedRecipeIds(selectedRecipeIds.filter(id => id !== recipe.id));
                                        }}
                                     />
                                     <label htmlFor={`r-${recipe.id}`} className="text-sm font-medium leading-none cursor-pointer flex-1 py-1">
                                         {recipe.title}
                                     </label>
                                 </div>
                             ))
                         )}
                    </ScrollArea>
                    <DialogFooter>
                        <div className="flex justify-between w-full items-center">
                            <span className="text-sm text-muted-foreground">{selectedRecipeIds.length} selected</span>
                            <Button onClick={handleGenerateFromRecipes} disabled={isGenerating || selectedRecipeIds.length === 0}>
                                {isGenerating ? "Generating..." : "Generate List"}
                            </Button>
                        </div>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function GroceryListDetail({ listId }: { listId: string }) {
    const { data: list, isLoading } = useGroceryList(listId);
    const { mutate: addItem } = useAddGroceryItem();
    const { mutate: updateItem } = useUpdateGroceryItem();
    const { mutate: deleteItem } = useDeleteGroceryItem();
    const { mutate: deleteList } = useDeleteGroceryList();
    const { mutate: updateList } = useUpdateGroceryList();
    const router = useRouter();

    const [newItemTerm, setNewItemTerm] = useState("");
    const [isRenaming, setIsRenaming] = useState(false);
    const [renameTitle, setRenameTitle] = useState("");

    // View Mode
    const [viewMode, setViewMode] = useState<'combined' | 'by-recipe'>('combined');
    
    useEffect(() => {
        if (list) {
            setRenameTitle(list.title);
            if (list.kind === 'generated') setViewMode('by-recipe');
            else setViewMode('combined');
        }
    }, [listId, list?.kind]); // Only when list ID/kind changes

    if (isLoading) return <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin text-muted-foreground" /></div>;
    if (!list) return <div className="p-8 text-center text-red-500">List not found</div>;

    const handleAddItem = () => {
        if (!newItemTerm.trim()) return;
        addItem({ listId, data: { display: newItemTerm } });
        setNewItemTerm("");
    };

    const handleDeleteList = () => {
        if (confirm("Are you sure you want to delete this list?")) {
            deleteList(listId, {
                onSuccess: () => {
                    // Update URL to remove list param handled by parent?
                    // No, parent sees invalidation and might not be able to clear selected ID automatically if list doesn't exist.
                    // We must force deselect.
                     // But we can't easily sync back to parent via prop.
                    // Rely on parent re-validating or simply redirect.
                    router.replace('/grocery');
                }
            });
        }
    };
    
    // Group Items
    const pendingItems = list.items?.filter(i => !i.checked) || [];
    const checkedItems = list.items?.filter(i => i.checked) || [];

    // Grouping for "By Recipe" view
    const getRecipeGroups = () => {
        const groups: Record<string, { title: string, items: any[] }> = {};
        const unassigned: any[] = [];
        
        list.items?.forEach(item => {
           if (item.checked) return; // Only show pending items in recipe cards for clarity? Or show all? Let's show pending only in main cards
           
           if (!item.sources || item.sources.length === 0) {
               unassigned.push(item);
               return;
           }
           item.sources.forEach((src: any) => {
                if (!groups[src.recipe_id]) {
                    groups[src.recipe_id] = { title: src.recipe_title, items: [] };
                }
                groups[src.recipe_id].items.push(item);
           });
        });

        return { groups, unassigned };
    };

    const { groups: recipeGroups, unassigned: unassignedItems } = viewMode === 'by-recipe' ? getRecipeGroups() : { groups: {}, unassigned: [] };
    const sortedGroupKeys = Object.keys(recipeGroups).sort((a,b) => recipeGroups[a].title.localeCompare(recipeGroups[b].title));

    return (
        <div className="flex flex-col h-full overflow-hidden">
             {/* Header */}
             <div className="p-4 border-b space-y-4 bg-card shrink-0">
                 <div className="flex items-start justify-between">
                     <div className="space-y-1">
                         {isRenaming ? (
                             <div className="flex gap-2">
                                 <Input 
                                    value={renameTitle} 
                                    onChange={e => setRenameTitle(e.target.value)} 
                                    className="h-8 w-64"
                                    autoFocus
                                 />
                                 <Button size="sm" onClick={() => {
                                     updateList({ id: listId, data: { title: renameTitle } });
                                     setIsRenaming(false);
                                 }}>Save</Button>
                             </div>
                         ) : (
                            <div className="flex items-center gap-2">
                                <h1 className="text-2xl font-bold">{list.title}</h1>
                                {list.kind === 'generated' && <Badge variant="secondary" className="text-xs">Generated</Badge>}
                            </div>
                         )}
                         <p className="text-xs text-muted-foreground">
                            {list.items?.length || 0} items • Created {format(new Date(list.created_at), "PP")}
                         </p>
                     </div>
                     
                     <DropdownMenu>
                         <DropdownMenuTrigger asChild>
                             <Button variant="ghost" size="icon"><MoreVertical className="w-4 h-4" /></Button>
                         </DropdownMenuTrigger>
                         <DropdownMenuContent align="end">
                             <DropdownMenuItem onClick={() => {
                                 setRenameTitle(list.title);
                                 setIsRenaming(true);
                             }}>
                                 Rename List
                             </DropdownMenuItem>
                             <DropdownMenuItem className="text-red-500" onClick={handleDeleteList}>
                                 <Trash2 className="w-4 h-4 mr-2" /> Delete List
                             </DropdownMenuItem>
                         </DropdownMenuContent>
                     </DropdownMenu>
                 </div>

                 {/* View Toggle (Only show for generated lists or if items have sources) */}
                 {(list.kind === 'generated' || list.items?.some(i => i.sources?.length > 0)) && (
                    <div className="flex items-center gap-2">
                        <div className="flex bg-muted p-1 rounded-lg">
                            <button 
                                onClick={() => setViewMode('by-recipe')}
                                className={cn("px-3 py-1 text-sm font-medium rounded-md transition-all", viewMode === 'by-recipe' ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground")}
                            >
                                By Recipe
                            </button>
                            <button 
                                onClick={() => setViewMode('combined')}
                                className={cn("px-3 py-1 text-sm font-medium rounded-md transition-all", viewMode === 'combined' ? "bg-background shadow text-foreground" : "text-muted-foreground hover:text-foreground")}
                            >
                                Combined
                            </button>
                        </div>
                    </div>
                 )}
             </div>

             {/* Add Item Bar */}
             <div className="p-4 bg-muted/20 shrink-0">
                 <div className="flex gap-2 max-w-2xl mx-auto">
                     <Input 
                        placeholder="Add item..." 
                        value={newItemTerm} 
                        onChange={e => setNewItemTerm(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleAddItem()}
                        className="bg-background shadow-sm"
                     />
                     <Button onClick={handleAddItem} disabled={!newItemTerm.trim()}>
                        <Plus className="w-4 h-4" />
                     </Button>
                 </div>
             </div>

             {/* Items List */}
             <ScrollArea className="flex-1 p-4">
                 <div className="max-w-2xl mx-auto space-y-6 pb-20">
                     
                     {/* Combined View */}
                     {viewMode === 'combined' && (
                         <div className="space-y-1">
                             {pendingItems.map(item => (
                                 <GroceryItemRow 
                                    key={item.id} 
                                    item={item} 
                                    listId={listId}
                                    onCheck={() => updateItem({ listId, itemId: item.id, data: { checked: true } })}
                                    onDelete={() => deleteItem({ listId, itemId: item.id })}
                                    showSource={true}
                                 />
                             ))}
                             {pendingItems.length === 0 && checkedItems.length === 0 && (
                                 <div className="text-center py-10 text-muted-foreground">List is empty</div>
                             )}
                         </div>
                     )}

                     {/* By Recipe View */}
                     {viewMode === 'by-recipe' && (
                         <div className="space-y-6">
                             {sortedGroupKeys.map(recipeId => (
                                 <Card key={recipeId}>
                                     <CardHeader className="py-3 px-4 bg-muted/30">
                                         <CardTitle className="text-base font-medium flex items-center justify-between">
                                             {recipeGroups[recipeId].title}
                                             <span className="text-xs font-normal text-muted-foreground">{recipeGroups[recipeId].items.length} items</span>
                                         </CardTitle>
                                     </CardHeader>
                                     <CardContent className="p-2 space-y-1">
                                         {recipeGroups[recipeId].items.map(item => (
                                             <GroceryItemRow 
                                                key={`${recipeId}-${item.id}`} // Unique key because item might appear in multiple groups
                                                item={item} 
                                                listId={listId}
                                                onCheck={() => updateItem({ listId, itemId: item.id, data: { checked: true } })}
                                                onDelete={() => deleteItem({ listId, itemId: item.id })}
                                                showSource={false} // Don't show source pill inside recipe card
                                             />
                                         ))}
                                     </CardContent>
                                 </Card>
                             ))}

                             {unassignedItems.length > 0 && (
                                 <Card>
                                     <CardHeader className="py-3 px-4 bg-muted/30">
                                        <CardTitle className="text-base font-medium">Other Items</CardTitle>
                                     </CardHeader>
                                     <CardContent className="p-2 space-y-1">
                                         {unassignedItems.map(item => (
                                             <GroceryItemRow 
                                                key={item.id}
                                                item={item}
                                                listId={listId}
                                                onCheck={() => updateItem({ listId, itemId: item.id, data: { checked: true } })}
                                                onDelete={() => deleteItem({ listId, itemId: item.id })}
                                                showSource={false}
                                             />
                                         ))}
                                     </CardContent>
                                 </Card>
                             )}

                             {/* If all items are checked */}
                             {sortedGroupKeys.length === 0 && unassignedItems.length === 0 && checkedItems.length === 0 && (
                                 <div className="text-center py-10 text-muted-foreground">List is empty</div>
                             )}
                          </div>
                     )}

                     {checkedItems.length > 0 && (
                         <>
                             <Separator />
                             <div className="space-y-1 opacity-60">
                                 <h4 className="text-sm font-medium mb-2">Checked Items</h4>
                                 {checkedItems.map(item => (
                                     <GroceryItemRow 
                                        key={item.id} 
                                        item={item} 
                                        listId={listId} 
                                        onCheck={() => updateItem({ listId, itemId: item.id, data: { checked: false } })}
                                        onDelete={() => deleteItem({ listId, itemId: item.id })}
                                        showSource={viewMode === 'combined'}
                                     />
                                 ))}
                             </div>
                         </>
                     )}
                 </div>
             </ScrollArea>
        </div>
    );
}

function GroceryItemRow({ item, listId, onCheck, onDelete, showSource=true }: { item: any, listId: string, onCheck: () => void, onDelete: () => void, showSource?: boolean }) {
    // Determine info text
    const infoParts = [];
    if (item.quantity) infoParts.push(`${item.quantity} ${item.unit || ''}`);
    const qtyInfo = infoParts.join(" ");

    return (
        <div className="group flex items-center gap-3 p-2 rounded hover:bg-muted/50 transition-colors">
            <Checkbox checked={item.checked} onCheckedChange={onCheck} className="rounded-full w-5 h-5 border-2" />
            <div className={cn("flex-1", item.checked && "line-through text-muted-foreground", "flex items-start justify-between gap-2")}>
                <div>
                     <div className="font-medium leading-normal">{item.display}</div>
                     {qtyInfo && <div className="text-xs text-muted-foreground">{qtyInfo}</div>}
                </div>
                
                {/* Source Pill */}
                {showSource && item.sources && item.sources.length > 0 && (
                    <div className="shrink-0">
                         {item.sources.length === 1 ? (
                             <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground px-2 py-0 h-5">
                                 {item.sources[0].recipe_title}
                             </Badge>
                         ) : (
                             <Popover>
                                 <PopoverTrigger asChild>
                                     <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100 cursor-pointer px-2 py-0 h-5">
                                         {item.sources.length} recipes
                                     </Badge>
                                 </PopoverTrigger>
                                 <PopoverContent className="w-64 p-2" align="end">
                                     <div className="text-xs font-medium mb-2 px-1">Used in:</div>
                                     <div className="space-y-1">
                                         {item.sources.map((s: any, idx: number) => (
                                             <div key={idx} className="text-xs p-1.5 rounded bg-muted/50 flex flex-col">
                                                 <span className="font-medium">{s.recipe_title}</span>
                                                 {/* Use 'line' from backend if available, or fallback */}
                                                 <span className="text-muted-foreground text-[10px] font-mono">{s.line || item.display}</span>
                                             </div>
                                         ))}
                                     </div>
                                 </PopoverContent>
                             </Popover>
                         )}
                    </div>
                )}
            </div>
            <Button variant="ghost" size="icon" className="opacity-0 group-hover:opacity-100 h-8 w-8 text-muted-foreground hover:text-red-500" onClick={onDelete}>
                <Trash2 className="w-4 h-4" />
            </Button>
        </div>
    );
}
