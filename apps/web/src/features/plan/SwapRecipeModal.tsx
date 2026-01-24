
"use client";

import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useRecipes } from "@/features/recipes/hooks";
import { cn } from "@/lib/utils";
import { Search, Loader2 } from "lucide-react";

interface SwapRecipeModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSelect: (recipeId: string) => void;
    currentRecipeId?: string;
    isPending?: boolean;
}

export function SwapRecipeModal({
    open,
    onOpenChange,
    onSelect,
    currentRecipeId,
    isPending
}: SwapRecipeModalProps) {
    const [search, setSearch] = useState("");
    const { data: recipes, isLoading } = useRecipes({ search });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md h-[400px] flex flex-col p-0 gap-0 overflow-hidden">
                <DialogHeader className="p-4 pb-2 border-b">
                    <DialogTitle>Swap Recipe</DialogTitle>
                </DialogHeader>

                <div className="p-4 pb-2">
                    <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search recipes..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="pl-9"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-2">
                    {isLoading ? (
                        <div className="flex items-center justify-center h-20 text-muted-foreground">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading...
                        </div>
                    ) : recipes?.length === 0 ? (
                        <div className="text-center p-8 text-sm text-muted-foreground">
                            No recipes found.
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {recipes?.map((recipe) => (
                                <button
                                    key={recipe.id}
                                    onClick={() => onSelect(recipe.id)}
                                    disabled={isPending}
                                    className={cn(
                                        "w-full text-left px-3 py-2 rounded-md transition-colors flex items-center justify-between group",
                                        recipe.id === currentRecipeId
                                            ? "bg-primary/10 text-primary font-medium"
                                            : "hover:bg-muted"
                                    )}
                                >
                                    <span className="truncate">{recipe.title}</span>
                                    {recipe.id === currentRecipeId && (
                                        <span className="text-xs ml-2 opacity-70">Current</span>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
