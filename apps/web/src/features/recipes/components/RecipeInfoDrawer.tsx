import { useState, useEffect } from "react";
import { Info, Loader2, Thermometer, Box, Sparkles, ChefHat, Save, Edit3, Bot, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { 
    useRecipeMacros, useEstimateMacros, useSaveMacros,
    useRecipeTipsDB, useEstimateTips, useSaveTips,
    useAIStatus,
    type RecipeMacroEntry, type RecipeTipEntry
} from "../hooks";

interface RecipeInfoDrawerProps {
    recipeId: string;
}

export function RecipeInfoDrawer({ recipeId }: RecipeInfoDrawerProps) {
    const [activeTab, setActiveTab] = useState<"macros" | "storage" | "reheat">("macros");
    const { data: aiStatus } = useAIStatus();

    const isAIEnabled = aiStatus?.ai_mode === "gemini" && aiStatus?.has_api_key;

    return (
        <Sheet>
            <SheetTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2 text-stone-600">
                    <Info className="h-4 w-4" />
                    Info
                </Button>
            </SheetTrigger>
            <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
                <SheetHeader>
                    <SheetTitle>Recipe Insights</SheetTitle>
                </SheetHeader>

                <div className="mt-6 w-full">
                    <div className="grid w-full grid-cols-3 bg-stone-100 p-1 rounded-lg mb-4">
                        {(["macros", "storage", "reheat"] as const).map((tab) => (
                            <button
                                key={tab}
                                onClick={() => setActiveTab(tab)}
                                className={cn(
                                    "text-xs font-semibold uppercase tracking-wider py-2 rounded-md transition-all",
                                    activeTab === tab 
                                        ? "bg-white text-stone-900 shadow-sm" 
                                        : "text-stone-500 hover:text-stone-700"
                                )}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>
                    
                    <div className="mt-4">
                        {activeTab === "macros" && (
                            <MacrosPanel recipeId={recipeId} isAIEnabled={!!isAIEnabled} />
                        )}
                        {activeTab === "storage" && (
                            <TipsPanel recipeId={recipeId} scope="storage" isAIEnabled={!!isAIEnabled} />
                        )}
                        {activeTab === "reheat" && (
                            <TipsPanel recipeId={recipeId} scope="reheat" isAIEnabled={!!isAIEnabled} />
                        )}
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}

// --- Macros Panel ---

function MacrosPanel({ recipeId, isAIEnabled }: { recipeId: string; isAIEnabled: boolean }) {
    const { data: savedEntry, isLoading: isLoadingSaved } = useRecipeMacros(recipeId);
    const { mutate: estimate, isPending: isEstimating } = useEstimateMacros();
    const { mutate: save, isPending: isSaving } = useSaveMacros();

    const [isEditing, setIsEditing] = useState(false);
    const [editValues, setEditValues] = useState<Partial<RecipeMacroEntry>>({});

    // Effect: Sync edit values when data loads
    useEffect(() => {
        if (savedEntry) {
            setEditValues(savedEntry);
        }
    }, [savedEntry]);

    const handleEstimate = () => {
        estimate({ recipeId, persist: true }, {
            onSuccess: () => {
                // Query invalidation handles reload
            }
        });
    };

    const handleSave = () => {
        save({ recipeId, data: { ...editValues, source: "user" } }, {
            onSuccess: () => setIsEditing(false)
        });
    };

    const displayEntry = savedEntry;
    const isLoading = isLoadingSaved || isEstimating;

    if (isLoading && !displayEntry) {
        return <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-stone-400" /></div>;
    }

    if (isEditing) {
        return (
            <div className="space-y-4 animate-in fade-in">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="text-xs font-semibold text-stone-500">Calories (Min-Max)</label>
                        <div className="flex gap-2 mt-1">
                            <Input 
                                type="number" placeholder="Min" 
                                value={editValues.calories_min || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, calories_min: parseInt(e.target.value) || null }))}
                            />
                            <Input 
                                type="number" placeholder="Max" 
                                value={editValues.calories_max || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, calories_max: parseInt(e.target.value) || null }))}
                            />
                        </div>
                    </div>
                    <div>
                        <label className="text-xs font-semibold text-stone-500">Protein (g)</label>
                        <div className="flex gap-2 mt-1">
                            <Input 
                                type="number" placeholder="Min" 
                                value={editValues.protein_min || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, protein_min: parseInt(e.target.value) || null }))}
                            />
                            <Input 
                                type="number" placeholder="Max" 
                                value={editValues.protein_max || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, protein_max: parseInt(e.target.value) || null }))}
                            />
                        </div>
                    </div>
                    <div>
                        <label className="text-xs font-semibold text-stone-500">Carbs (g)</label>
                        <div className="flex gap-2 mt-1">
                            <Input 
                                type="number" placeholder="Min" 
                                value={editValues.carbs_min || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, carbs_min: parseInt(e.target.value) || null }))}
                            />
                            <Input 
                                type="number" placeholder="Max" 
                                value={editValues.carbs_max || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, carbs_max: parseInt(e.target.value) || null }))}
                            />
                        </div>
                    </div>
                    <div>
                        <label className="text-xs font-semibold text-stone-500">Fat (g)</label>
                        <div className="flex gap-2 mt-1">
                            <Input 
                                type="number" placeholder="Min" 
                                value={editValues.fat_min || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, fat_min: parseInt(e.target.value) || null }))}
                            />
                            <Input 
                                type="number" placeholder="Max" 
                                value={editValues.fat_max || ''} 
                                onChange={e => setEditValues(prev => ({ ...prev, fat_max: parseInt(e.target.value) || null }))}
                            />
                        </div>
                    </div>
                </div>
                
                <div className="flex gap-2 justify-end pt-4">
                    <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                    <Button size="sm" onClick={handleSave} disabled={isSaving}>
                        {isSaving ? <Loader2 className="h-3 w-3 animate-spin mr-2"/> : <Save className="h-3 w-3 mr-2"/>}
                        Save Changes
                    </Button>
                </div>
            </div>
        )
    }

    if (!displayEntry) {
        return (
            <div className="flex flex-col items-center justify-center py-10 text-center space-y-4">
                 <div className="p-4 bg-stone-100 rounded-full text-stone-400">
                    <Sparkles className="h-6 w-6" />
                 </div>
                 <div>
                    <h4 className="font-semibold text-stone-900">No macro data</h4>
                    <p className="text-stone-500 text-sm mt-1">
                        Estimate calories and protein from ingredients.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => { setEditValues({}); setIsEditing(true); }}>Add Manually</Button>
                    <Button onClick={handleEstimate} disabled={isEstimating}>
                        {isEstimating ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : (isAIEnabled ? <Bot className="h-4 w-4 mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>)}
                        {isAIEnabled ? "Estimate with AI" : "Estimate (Heuristic)"}
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
            <div className="flex justify-between items-center mb-2">
                <Badge variant="secondary" className={cn(
                    "flex gap-1 items-center",
                    displayEntry.source === 'ai' ? "bg-purple-100 text-purple-700 hover:bg-purple-100" 
                    : displayEntry.source === 'heuristic' ? "bg-amber-100 text-amber-700 hover:bg-amber-100"
                    : "bg-blue-100 text-blue-700 hover:bg-blue-100"
                )}>
                    {displayEntry.source === 'ai' && <Bot className="h-3 w-3" />}
                    {displayEntry.source === 'heuristic' && <AlertCircle className="h-3 w-3" />}
                    {displayEntry.source === 'user' && <Edit3 className="h-3 w-3" />}
                    
                    {displayEntry.source === 'ai' ? "AI Estimate" 
                       : displayEntry.source === 'heuristic' ? "Heuristic Estimate" 
                       : "User Entry"}
                </Badge>
                
                <div className="flex gap-1">
                     <Button variant="ghost" size="sm" onClick={handleEstimate} disabled={isEstimating} title="Re-estimate">
                        <Bot className="h-4 w-4 text-stone-400" />
                     </Button>
                     <Button variant="ghost" size="sm" onClick={() => { setEditValues(displayEntry); setIsEditing(true); }}>
                        <Edit3 className="h-4 w-4 text-stone-400" />
                     </Button>
                </div>
            </div>

            <div className="bg-stone-50/50 p-4 rounded-lg border border-stone-100">
                <div className="grid grid-cols-2 gap-4 text-center">
                    <div>
                        <div className="text-2xl font-bold text-stone-800">
                            {displayEntry.calories_min}-{displayEntry.calories_max}
                        </div>
                        <div className="text-xs uppercase font-bold text-stone-400 tracking-wider">Calories</div>
                    </div>
                    <div>
                        <div className="text-2xl font-bold text-stone-800">
                            {displayEntry.protein_min}-{displayEntry.protein_max}g
                        </div>
                        <div className="text-xs uppercase font-bold text-stone-400 tracking-wider">Protein</div>
                    </div>
                    {(displayEntry.carbs_min !== null || displayEntry.carbs_max !== null) && (
                        <div>
                            <div className="text-2xl font-bold text-stone-800">
                                {displayEntry.carbs_min}-{displayEntry.carbs_max}g
                            </div>
                            <div className="text-xs uppercase font-bold text-stone-400 tracking-wider">Carbs</div>
                        </div>
                    )}
                    {(displayEntry.fat_min !== null || displayEntry.fat_max !== null) && (
                        <div>
                            <div className="text-2xl font-bold text-stone-800">
                                {displayEntry.fat_min}-{displayEntry.fat_max}g
                            </div>
                            <div className="text-xs uppercase font-bold text-stone-400 tracking-wider">Fat</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}


// --- Tips Panel ---

function TipsPanel({ recipeId, scope, isAIEnabled }: { recipeId: string, scope: "storage" | "reheat", isAIEnabled: boolean }) {
    const { data: savedEntry, isLoading: isLoadingSaved } = useRecipeTipsDB(recipeId, scope);
    const { mutate: estimate, isPending: isEstimating } = useEstimateTips();
    const { mutate: save, isPending: isSaving } = useSaveTips();

    const [isEditing, setIsEditing] = useState(false);
    const [editText, setEditText] = useState("");

    useEffect(() => {
        if (savedEntry) {
            setEditText(savedEntry.tips_json.join("\n"));
        }
    }, [savedEntry]);

    const handleEstimate = () => {
        estimate({ recipeId, scope, persist: true }, {
            onSuccess: (data) => {
                // Invalidation should handle update
            }
        });
    };

    const handleSave = () => {
        const tips = editText.split("\n").filter(t => t.trim().length > 0);
        save({ recipeId, scope, data: { tips_json: tips, source: "user" } }, {
            onSuccess: () => {
                setIsEditing(false);
            }
        });
    };
    
    const displayEntry = savedEntry;
    const isLoading = isLoadingSaved || isEstimating;

    if (isLoading && !displayEntry) {
        return <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-stone-400" /></div>;
    }

    if (isEditing) {
        return (
             <div className="space-y-4 animate-in fade-in">
                 <div className="space-y-2">
                     <label className="text-xs font-semibold text-stone-500">
                         {scope === "storage" ? "Storage Tips" : "Reheating Instructions"} (One per line)
                     </label>
                     <Textarea 
                         value={editText} 
                         onChange={e => setEditText(e.target.value)} 
                         rows={8}
                     />
                 </div>
                 <div className="flex gap-2 justify-end">
                     <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>Cancel</Button>
                     <Button size="sm" onClick={handleSave} disabled={isSaving}>Save</Button>
                 </div>
             </div>
        )
    }

    if (!displayEntry) {
        return (
            <div className="flex flex-col items-center justify-center py-10 text-center space-y-4">
                 <div className="p-4 bg-stone-100 rounded-full text-stone-400">
                    {scope === "storage" ? <Box className="h-6 w-6" /> : <Thermometer className="h-6 w-6" />}
                 </div>
                 <div>
                    <h4 className="font-semibold text-stone-900">No {scope} tips</h4>
                    <p className="text-stone-500 text-sm mt-1">
                        Add your own or get an AI estimate.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => { setEditText(""); setIsEditing(true); }}>Add Manually</Button>
                    <Button onClick={handleEstimate} disabled={isEstimating}>
                        {isEstimating ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : (isAIEnabled ? <Bot className="h-4 w-4 mr-2"/> : <Sparkles className="h-4 w-4 mr-2"/>)}
                        {isAIEnabled ? "Estimate with AI" : "Estimate (Heuristic)"}
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
             <div className="flex justify-between items-center mb-2">
                 <Badge variant="secondary" className={cn(
                     "flex gap-1 items-center",
                     displayEntry.source === 'ai' ? "bg-purple-100 text-purple-700 hover:bg-purple-100" 
                     : displayEntry.source === 'heuristic' ? "bg-amber-100 text-amber-700 hover:bg-amber-100"
                     : "bg-blue-100 text-blue-700 hover:bg-blue-100"
                 )}>
                     {displayEntry.source === 'ai' && <Bot className="h-3 w-3" />}
                     {displayEntry.source === 'heuristic' && <AlertCircle className="h-3 w-3" />}
                     {displayEntry.source === 'user' && <Edit3 className="h-3 w-3" />}

                     {displayEntry.source === 'ai' ? "AI Estimate" 
                        : displayEntry.source === 'heuristic' ? "Heuristic Estimate" 
                        : "User Entry"}
                 </Badge>
                 <div className="flex gap-1">
                     <Button variant="ghost" size="sm" onClick={handleEstimate} disabled={isEstimating} title="Re-estimate">
                        <Bot className="h-4 w-4 text-stone-400" />
                     </Button>
                     <Button variant="ghost" size="icon" onClick={() => { setEditText(displayEntry.tips_json.join("\n")); setIsEditing(true); }}>
                        <Edit3 className="h-4 w-4 text-stone-400" />
                     </Button>
                 </div>
             </div>

            <div className="bg-stone-50/50 p-4 rounded-lg border border-stone-100 space-y-4">
                <ul className="space-y-3">
                    {displayEntry.tips_json.map((tip, i) => (
                        <li key={i} className="text-sm text-stone-700 flex gap-2 items-start">
                            <span className="text-purple-400 mt-1.5">•</span>
                            <span className="leading-relaxed">{tip}</span>
                        </li>
                    ))}
                </ul>
            </div>
            
            {(displayEntry.food_safety_json?.length ?? 0) > 0 && (
                 <div className="bg-amber-50 border border-amber-100 rounded-md p-4">
                    <h4 className="text-xs font-bold uppercase text-amber-800 mb-2 flex items-center gap-1.5">
                        <ChefHat className="h-3 w-3" /> Food Safety Note
                    </h4>
                    <ul className="space-y-1">
                        {displayEntry.food_safety_json.map((fs, i) => (
                            <li key={i} className="text-xs text-amber-900 flex gap-2">
                                <span>•</span> {fs}
                            </li>
                        ))}
                    </ul>
                 </div>
            )}
        </div>
    );
}
