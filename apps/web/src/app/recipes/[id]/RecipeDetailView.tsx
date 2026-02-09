'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
    ArrowLeft,
    ChefHat,
    Flame,
    Loader2,
    Clock,
    Users,
    Sparkles,
    RefreshCw,
    CalendarPlus
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Button } from '@/components/ui/button';
import { AddToPlanModal } from '@/features/plan/AddToPlanModal';
import {
    useRecipe,
    useAnalyzeMacros,
    useGenerateImage,
    useImageStatus,
    useRegenerateImage,
    useAIStatus
} from '@/features/recipes/hooks';
import { useQueryClient } from '@tanstack/react-query';
import type { RecipeStep, Recipe } from '@/lib/api';
import { ShareRecipeModal } from '@/features/recipes/ShareRecipeModal';
import { SubstituteModal } from '@/features/recipes/SubstituteModal';
import { RecipeNotesHistory } from '@/features/recipes/RecipeNotesHistory';
import { RecipeAssistPanel } from '@/features/recipes/components/RecipeAssistPanel';
import { InsightsCard } from '@/features/insights/InsightsCard';
import { IngredientRow } from '@/features/recipes/components/IngredientRow';
import { RecipeLearningsCard } from '@/features/recipes/components/RecipeLearningsCard';
import { RecipeInfoDrawer } from '@/features/recipes/components/RecipeInfoDrawer';
import { useUnitPrefs } from '@/features/preferences/hooks';
import { cleanTitle, cleanLine } from "@/lib/recipeSanitize";
import { formatDurationPill } from "@/lib/format";
import { toStructuredStep } from "@/lib/stepFormat";
import {
    useCookSessionStart,
} from '@/features/cook/hooks';

// Duplicate helper for now
interface CookStep {
    title: string;
    minutes: number;
    bullets: string[];
    tip?: string;
}
function apiStepToCookStep(step: RecipeStep): CookStep {
    return {
        title: cleanLine(step.title || ""),
        minutes: step.minutes_est ?? 5,
        bullets: (step.bullets || []).map(cleanLine),
    };
}


// --- Local Components (Hero, MacroBadge) ---

function MacroBadge({ recipeId }: { recipeId: string }) {
    const { mutate, data, isPending } = useAnalyzeMacros();

    if (data) {
        const caloriesText = data.calories_range
            ? `${data.calories_range.min}-${data.calories_range.max} cal`
            : '';
        const proteinText = data.protein_range
            ? ` • ${data.protein_range.min}-${data.protein_range.max}g protein`
            : '';
        const tagsText = data.tags?.join(', ') || '';

        return (
            <div className="flex items-center gap-2 animate-in fade-in" title={data.disclaimer}>
                <Sparkles className="h-4 w-4 text-purple-500" />
                <span className="font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-100 text-xs uppercase tracking-tight">
                    {tagsText} ({caloriesText}{proteinText})
                </span>
                <span className="text-[10px] text-stone-400 uppercase">{data.confidence}</span>
            </div>
        );
    }

    return (
        <button
            onClick={() => mutate(recipeId)}
            disabled={isPending}
            className="flex items-center gap-2 text-stone-400 hover:text-stone-600 transition-colors"
            title="Analyze Nutrition (AI)"
        >
            <Sparkles className={cn("h-4 w-4", isPending && "animate-pulse text-purple-400")} />
            <span className="text-xs font-semibold">{isPending ? "Analyzing..." : "Analyze"}</span>
        </button>
    );
}

function RecipeHero({ recipe }: { recipe: Recipe }) {
    const { mutate: generateImage, isPending: isGeneratingMsg, error: genError } = useGenerateImage();
    const { mutate: regenerateImage } = useRegenerateImage();
    const { data: imageStatus } = useImageStatus(recipe.id);
    const { data: aiStatus } = useAIStatus();
    const [isAddToPlanOpen, setIsAddToPlanOpen] = useState(false);

    const activeImageUrl = imageStatus?.public_url || recipe.primary_image_url;
    const isGenerating = imageStatus?.status === 'pending' || isGeneratingMsg;
    const isQuotaError = genError?.message?.includes("429") || aiStatus?.images_status === 'quota_exceeded';

    const handleGenerate = () => generateImage(recipe.id);
    const handleRegenerate = () => regenerateImage(recipe.id);

    // Determine time to show
    const timeLabel = formatDurationPill(recipe.total_minutes || recipe.time_minutes, {
        estimated: recipe.total_minutes_source === 'estimated'
    });

    return (
        <div className="overflow-hidden rounded-[2.5rem] border border-amber-100/50 bg-white shadow-lg relative group">
            <div className="relative aspect-[16/9] bg-amber-50">
                {activeImageUrl ? (
                    <img
                        src={activeImageUrl}
                        alt={recipe.title}
                        className="h-full w-full object-cover"
                    />
                ) : (
                    <div className="h-full w-full flex items-center justify-center bg-amber-50/50">
                        <ChefHat className="h-20 w-20 text-amber-200/50" />
                    </div>
                )}

                {/* Overlay Gradient */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />

                {/* Add to Plan Button (Top Left) */}
                <div className="absolute top-4 left-4 z-20">
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-9 gap-2 rounded-full bg-black/20 text-white backdrop-blur-md hover:bg-black/40 border border-white/10 px-3"
                        onClick={() => setIsAddToPlanOpen(true)}
                    >
                        <CalendarPlus className="h-4 w-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">Add to Plan</span>
                    </Button>
                </div>

                {/* 
                {/* Generate/Regenerate UI */}
                <div className="absolute top-4 right-4 z-20">
                    {/* Regenerate Button (only if image exists and not generating) */}
                    {activeImageUrl && !isGenerating && aiStatus?.images_available && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-9 w-9 rounded-full bg-black/20 text-white backdrop-blur-md hover:bg-black/40 border border-white/10"
                            onClick={handleRegenerate}
                            title="Regenerate Image"
                        >
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                    )}
                </div>

                {/* Center Action (Empty State or Generating) */}
                {!activeImageUrl && !isGenerating && (
                    <div className="absolute inset-0 flex items-center justify-center z-10">
                        <Button
                            onClick={handleGenerate}
                            disabled={!aiStatus?.images_available || isQuotaError}
                            className={cn(
                                "h-12 gap-2 rounded-full border border-amber-200/50 bg-white/90 px-6 text-stone-800 shadow-xl backdrop-blur-sm hover:bg-white",
                                (!aiStatus?.images_available || isQuotaError) && "opacity-70 cursor-not-allowed grayscale"
                            )}
                        >
                            <Sparkles className={cn("h-4 w-4", (aiStatus?.images_available && !isQuotaError) ? "text-amber-500" : "text-stone-400")} />
                            <span className="font-bold text-xs uppercase tracking-widest">
                                {isQuotaError 
                                    ? "Quota Limit Reached" 
                                    : (aiStatus?.images_available ? "Generate Image" : "AI Images Disabled")}
                            </span>
                        </Button>
                    </div>
                )}

                {/* Loading State Overlay */}
                {isGenerating && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/10 backdrop-blur-[2px]">
                        <div className="rounded-2xl bg-white/90 p-4 shadow-xl backdrop-blur-md">
                            <Loader2 className="h-6 w-6 animate-spin text-amber-500" />
                        </div>
                        <p className="mt-3 rounded-lg bg-black/40 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                            Generating...
                        </p>
                    </div>
                )}

                {/* Title & Metadata (Bottom) */}
                <div className="absolute bottom-6 left-6 right-6 z-10">
                    <h1 className="font-serif text-3xl leading-tight text-white drop-shadow-md">{cleanTitle(recipe.title)}</h1>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {timeLabel && (
                           <span className="flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md tabular-nums">
                               <Clock className="h-3 w-3" />
                               {timeLabel}
                           </span>
                        )}
                        {recipe.cuisines?.map((c) => (
                            <span key={c} className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                                {c}
                            </span>
                        ))}
                        {recipe.tags?.map((t) => (
                            <span key={t} className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                                {t}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Meta info Panel */}
            <div className="p-6 relative bg-white">
                <div className="flex items-center gap-6 text-sm text-stone-600">
                    {recipe.servings && (
                        <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-amber-600" />
                            <span className="font-semibold">{recipe.servings} servings</span>
                        </div>
                    )}
                    <MacroBadge recipeId={recipe.id} />
                    <div className="flex items-center gap-2">
                        <Flame className="h-4 w-4 text-amber-600" />
                        <span className="font-semibold">{recipe.steps.length} steps</span>
                    </div>
                </div>

                {/* Legacy Notes - Hidden if history exists */}
                {recipe.notes ? (
                    <details className="mt-4">
                        <summary className="text-xs font-bold uppercase tracking-widest text-stone-400 cursor-pointer hover:text-amber-600 transition-colors select-none">

            <AddToPlanModal
                open={isAddToPlanOpen}
                onOpenChange={setIsAddToPlanOpen}
                recipeId={recipe.id}
                recipeTitle={recipe.title}
            />
                            Show Legacy Notes Log
                        </summary>
                        <p className="mt-4 text-sm text-stone-600 leading-relaxed whitespace-pre-wrap pl-4 border-l-2 border-stone-100">{recipe.notes}</p>
                    </details>
                ) : null}

                <div className="mt-6 space-y-6">
                    <RecipeLearningsCard recipeId={recipe.id} />
                    <InsightsCard scope="recipe" recipeId={recipe.id} />
                </div>

                <RecipeNotesHistory recipeId={recipe.id} />
            </div>
        </div>
    );
}

function RecipeIngredients({ recipe }: { recipe: Recipe }) {
    const { data: prefs, isSuccess } = useUnitPrefs();
    const [mode, setMode] = useState<'default' | 'metric' | 'imperial'>('default');
    
    // Sync mode with prefs
    useEffect(() => {
        if (isSuccess && prefs) {
            const target = prefs.system === 'metric' ? 'metric' : 'imperial';
            // Only auto-switch if user hasn't manually interacted yet? 
            // For now, always sync to workspace pref on load ensures consistency.
            setMode(target);
        }
    }, [isSuccess, prefs?.system]); // Key on system change

    const handleModeChange = (m: 'default' | 'metric' | 'imperial') => {
        setMode(m);
    };

    if (!recipe.ingredients?.length) return null;

    return (
        <div className="mt-8">
            <div className="flex items-center justify-between mb-4">
                <div className="flex flex-col">
                    <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-stone-900 flex items-center gap-2">
                        <ChefHat className="h-4 w-4 text-amber-600" />
                        Ingredients ({recipe.ingredients.length})
                    </h2>
                    {mode !== 'default' && (
                        <span className="text-[10px] font-bold text-amber-600 mt-1 ml-6 animate-in fade-in">
                            Using: {mode === 'metric' ? 'Metric' : 'US Customary'}
                        </span>
                    )}
                </div>
                
                 <div className="flex bg-stone-100/50 rounded-lg p-1 border border-stone-100">
                     <button onClick={() => handleModeChange('default')} className={cn("px-2 py-1 text-[10px] uppercase font-bold rounded-md transition-all", mode === 'default' ? "bg-white shadow-sm text-stone-900 ring-1 ring-stone-900/5" : "text-stone-400 hover:text-stone-600")}>Default</button>
                     <button onClick={() => handleModeChange('metric')} className={cn("px-2 py-1 text-[10px] uppercase font-bold rounded-md transition-all", mode === 'metric' ? "bg-white shadow-sm text-stone-900 ring-1 ring-stone-900/5" : "text-stone-400 hover:text-stone-600")}>Metric</button>
                     <button onClick={() => handleModeChange('imperial')} className={cn("px-2 py-1 text-[10px] uppercase font-bold rounded-md transition-all", mode === 'imperial' ? "bg-white shadow-sm text-stone-900 ring-1 ring-stone-900/5" : "text-stone-400 hover:text-stone-600")}>Imp</button>
                 </div>
            </div>

            <div className="space-y-2">
                {recipe.ingredients.map((ing, i) => (
                    <IngredientRow 
                        key={i} 
                        ingredient={ing} 
                        scaleFactor={1} 
                        mode={mode} 
                    />
                ))}
            </div>
        </div>
    );
}

// --- Main View Component ---

export function RecipeDetailView({ recipeId }: { recipeId: string }) {
    const router = useRouter();
    const queryClient = useQueryClient();

    const { data: recipe, isLoading, error } = useRecipe(recipeId);
    const startSessionMutation = useCookSessionStart();
    const [subOpen, setSubOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<'overview' | 'assist'>('overview');

    const handleStartCooking = () => {
        // Start session then redirect
        startSessionMutation.mutate(recipeId, {
            onSuccess: (data) => {
                // Invalidate query to ensure fresh data
                queryClient.setQueryData(['cook-session', 'active', recipeId], data);
                // Redirect to Cook Mode
                router.replace(`/recipes/${recipeId}?cook=1`);
            },
            onError: (e) => {
                console.error("Failed to start session", e);
            }
        });
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
            </div>
        );
    }

    if (error || !recipe) {
        return (
            <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center p-6">
                <div className="rounded-[2.5rem] border border-red-100 bg-red-50 p-8 text-center max-w-md">
                    <p className="font-semibold text-red-800">Recipe not found</p>
                    <Button variant="outline" className="mt-4" onClick={() => router.push('/recipes')}>
                        Back to recipes
                    </Button>
                </div>
            </div>
        );
    }

    const cookSteps: CookStep[] = recipe?.steps.map(apiStepToCookStep) ?? [];

    return (
        <div className="min-h-screen bg-[#FAF9F6]">
            {/* Subtle amber wash */}
            <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-amber-50/60 via-transparent to-transparent" />

            <SubstituteModal
                open={subOpen}
                onOpenChange={setSubOpen}
                recipeContext={recipe?.title}
            />

            <div className="relative mx-auto max-w-2xl px-6 pt-6 pb-32">
                {/* Header (Back + Share) */}
                <div className="mb-6 flex items-center justify-between">
                    <button
                        onClick={() => router.push('/recipes')}
                        className="flex items-center gap-2 text-stone-500 hover:text-stone-700 transition-colors"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span className="text-sm font-semibold">Back to recipes</span>
                    </button>

                    <div className="flex items-center gap-2">
                        <RecipeInfoDrawer recipeId={recipeId} />
                        <ShareRecipeModal recipeId={recipeId} />
                    </div>
                </div>

                {/* Hero */}
                <RecipeHero recipe={recipe} />

                {/* Tabs */}
                <div className="mt-8 mb-6 border-b border-stone-100">
                    <div className="flex gap-8">
                        <button 
                            onClick={() => setActiveTab('overview')}
                            className={cn(
                                "pb-3 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2", 
                                activeTab === 'overview' 
                                    ? "border-amber-500 text-stone-900" 
                                    : "border-transparent text-stone-400 hover:text-stone-600"
                            )}
                        >
                            Overview
                        </button>
                        <button 
                            onClick={() => setActiveTab('assist')}
                            className={cn(
                                "pb-3 text-xs font-black uppercase tracking-[0.2em] transition-all border-b-2 flex items-center gap-2", 
                                activeTab === 'assist' 
                                    ? "border-amber-500 text-stone-900" 
                                    : "border-transparent text-stone-400 hover:text-stone-600"
                            )}
                        >
                            <Sparkles className={cn("h-3 w-3", activeTab === 'assist' ? "text-amber-500" : "text-stone-300")} />
                            Ask Chef
                        </button>
                    </div>
                </div>

                {activeTab === 'overview' ? (
                    <>
                        {/* Ingredients */}
                        <RecipeIngredients recipe={recipe} />

                        {/* Steps Preview */}
                        <div className="mt-8">
                            <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-stone-900 flex items-center gap-2 mb-4">
                                <Flame className="h-4 w-4 text-amber-600" />
                                Cooking Steps ({cookSteps.length})
                            </h2>

                            <div className="space-y-3">
                                {cookSteps.slice(0, 3).map((step, i) => (
                                    <div key={i} className="rounded-[2rem] border border-amber-100/50 bg-white p-5 shadow-sm">
                                        <div className="flex items-center gap-3">
                                            <div className="grid h-8 w-8 place-items-center rounded-xl bg-amber-50 border border-amber-100 text-amber-900">
                                                <span className="text-xs font-black">{i + 1}</span>
                                            </div>
                                            <div className="flex-1">
                                                <div className="font-semibold text-stone-900 leading-snug">{step.title}</div>
                                                {step.bullets && step.bullets.length > 0 && (
                                                    <ul className="mt-2 space-y-1 text-sm text-stone-600">
                                                        {step.bullets.map((b, idx) => (
                                                            <li key={idx} className="flex gap-2">
                                                                <span className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-stone-300" />
                                                                <span className="min-w-0 flex-1 whitespace-normal break-words leading-snug">{b}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                )}
                                                <p className="mt-2 text-[10px] font-black uppercase tracking-widest text-stone-400">~{step.minutes} min</p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                                {cookSteps.length > 3 && (
                                    <p className="text-center text-sm text-stone-400">+{cookSteps.length - 3} more steps</p>
                                )}
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <RecipeAssistPanel 
                            recipeId={recipeId} 
                            recipe={recipe} 
                        />
                    </div>
                )}
            </div>

            {/* Floating Start Cook Mode Button */}
            <div className="fixed bottom-6 left-0 right-0 px-6 z-40">
                <div className="mx-auto max-w-2xl">
                    <button
                        type="button"
                        onClick={handleStartCooking}
                        disabled={startSessionMutation.isPending}
                        className={cn(
                            "flex w-full items-center justify-center gap-3 rounded-[2rem] bg-stone-900 py-5 text-xs font-black uppercase tracking-[0.3em] text-white shadow-2xl transition-all active:scale-95 hover:bg-stone-800",
                            startSessionMutation.isPending && "opacity-70 cursor-not-allowed"
                        )}
                    >
                        {startSessionMutation.isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Flame className="h-5 w-5 text-amber-400" />}
                        {startSessionMutation.isPending ? "Starting..." : "Start Cook Mode"}
                    </button>
                </div>
            </div>

            <style>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
        </div>
    );
}
