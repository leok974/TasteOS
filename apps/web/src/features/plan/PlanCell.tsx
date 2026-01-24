
import { useState } from 'react';
import { PlanEntry, useUpdateEntry } from './hooks';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, RotateCcw } from 'lucide-react';
import { SwapRecipeModal } from './SwapRecipeModal';

interface PlanCellProps {
    entry?: PlanEntry;
    type: 'lunch' | 'dinner';
}

export function PlanCell({ entry, type }: PlanCellProps) {
    const [isSwapOpen, setIsSwapOpen] = useState(false);
    const { updateEntry } = useUpdateEntry();

    if (!entry) {
        return (
            <div className="h-full w-full rounded-lg border-2 border-dashed border-muted flex items-center justify-center text-muted-foreground text-sm p-4 text-center">
                Empty
            </div>
        );
    }

    const handleSwap = (recipeId: string) => {
        updateEntry(entry.id, {
            recipe_id: recipeId,
            is_leftover: false // Reset leftover status on manual swap
        });
        setIsSwapOpen(false);
    };

    // Determine variant based on leftover
    const isLeftover = entry.is_leftover;

    return (
        <>
            <Card
                onClick={() => setIsSwapOpen(true)}
                className={cn(
                    "h-full p-3 flex flex-col justify-between transition-all hover:ring-2 hover:ring-primary/20 cursor-pointer group relative",
                    isLeftover ? "bg-muted/30" : "bg-card"
                )}
            >
                {/* Hover hint */}
                <div className="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-lg pointer-events-none">
                    <Badge variant="secondary" className="bg-background/80 backdrop-blur shadow-sm">
                        <RotateCcw className="w-3 h-3 mr-1" /> Swap
                    </Badge>
                </div>

                <div>
                    <div className="flex items-start justify-between gap-1 mb-2">
                        {isLeftover && (
                            <Badge variant="secondary" className="text-[10px] h-5 px-1.5 flex gap-1 items-center">
                                <RefreshCw className="w-3 h-3" />
                                Leftover
                            </Badge>
                        )}
                        {entry.method_choice && !isLeftover && (
                            <Badge variant="outline" className="text-[10px] h-5 px-1.5 ml-auto">
                                {entry.method_choice}
                            </Badge>
                        )}
                    </div>

                    <h4 className={cn("font-medium text-sm leading-tight line-clamp-2", !entry.recipe_id && "text-muted-foreground italic")}>
                        {entry.recipe_title || (isLeftover ? "Leftovers" : "No Recipe")}
                    </h4>
                </div>

                {/* Footer / Method details (future) */}
                <div className="mt-2 text-xs text-muted-foreground/80">
                    {entry.method_options_json?.["Stove"]?.time && (
                        <span>⏱ {entry.method_options_json["Stove"].time}</span>
                    )}
                </div>
            </Card>

            <SwapRecipeModal
                open={isSwapOpen}
                onOpenChange={setIsSwapOpen}
                onSelect={handleSwap}
                currentRecipeId={entry.recipe_id}
            />
        </>
    );
}
