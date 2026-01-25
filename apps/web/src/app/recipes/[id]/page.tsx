'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import {
    ArrowLeft,
    CheckCircle2,
    ChefHat,
    ChevronRight,
    Clock,
    Flame,
    Loader2,
    Users,
    X,
    Sparkles,
    RefreshCw,
    Check,
    Minus,
    Plus,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
    useRecipe,
    useImageStatus,
    useGenerateImage,
    useRegenerateImage,
    useAnalyzeMacros,
    recipeKeys
} from '@/features/recipes/hooks';
import { useQueryClient } from '@tanstack/react-query';
import type { RecipeStep, Recipe } from '@/lib/api';
import { ShareRecipeModal } from '@/features/recipes/ShareRecipeModal';
import { SubstituteModal } from '@/features/recipes/SubstituteModal';
import {
    useCookSessionActive,
    useCookSessionStart,
    useCookSessionPatch,
    useCookSessionEnd,
    useCookSessionEvents
} from '@/features/cook/hooks';
import { MethodSwitcher } from '@/features/cook/MethodSwitcher';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { TimerManager } from '@/features/cook/TimerManager';
import { AssistPanel } from '@/features/cook/AssistPanel';
import { AdjustButtons } from '@/features/cook/AdjustButtons';

// Convert API step to CookStep format
interface CookStep {
    title: string;
    minutes: number;
    bullets: string[];
    tip?: string;
}

function apiStepToCookStep(step: RecipeStep): CookStep {
    return {
        title: step.title,
        minutes: step.minutes_est ?? 5,
        bullets: step.bullets ?? [],
    };
}

// --- Imports ---

import type { CookSession } from '@/features/cook/hooks';

// --- Helpers ---

function formatQty(qty: number) {
    const decimal = qty % 1;
    const whole = Math.floor(qty);
    let fraction = '';

    if (Math.abs(decimal - 0.5) < 0.01) fraction = '½';
    else if (Math.abs(decimal - 0.25) < 0.01) fraction = '¼';
    else if (Math.abs(decimal - 0.75) < 0.01) fraction = '¾';
    else if (Math.abs(decimal - 0.33) < 0.02) fraction = '⅓';
    else if (Math.abs(decimal - 0.66) < 0.02) fraction = '⅔';

    if (whole === 0 && fraction) return fraction;
    if (whole > 0 && fraction) return `${whole} ${fraction}`;
    return Number(qty.toFixed(2)).toString();
}

function IngredientsView({
    ingredients,
    baseServings,
    targetServings
}: {
    ingredients: Recipe['ingredients'];
    baseServings: number;
    targetServings: number;
}) {
    if (!ingredients || ingredients.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-center bg-stone-50/50 rounded-2xl border border-stone-100">
                <p className="text-stone-400 text-sm font-medium">No ingredients listed</p>
            </div>
        );
    }

    const factor = targetServings / (baseServings || 1);

    return (
        <div className="space-y-2">
            {ingredients.map((ing, i) => {
                const scaledQty = ing.qty ? ing.qty * factor : null;
                return (
                    <div key={i} className="flex items-center gap-3 p-3 rounded-2xl bg-white border border-amber-100/50 shadow-sm">
                        <div className="h-2 w-2 rounded-full bg-amber-200 flex-shrink-0" />
                        <div className="flex-1 text-sm font-medium text-stone-700">
                            {ing.name}
                        </div>
                        {scaledQty !== null && (
                            <div className="text-sm font-bold text-amber-900 bg-amber-50 px-2 py-1 rounded-lg">
                                {formatQty(scaledQty)} <span className="text-xs font-normal text-amber-700">{ing.unit}</span>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
function StepCard({
    step,
    index,
    active,
    checks,
    onToggle,
    showIndex = true,
    showBadge = true,
}: {
    step: CookStep;
    index: number;
    active: boolean;
    checks: Record<string, boolean>;
    onToggle: (key: string) => void;
    showIndex?: boolean;
    showBadge?: boolean;
}) {
    return (
        <Card
            className={cn(
                "rounded-[2.5rem] border-amber-100/50 shadow-sm",
                active ? "bg-white" : "bg-white/70"
            )}
        >
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {showIndex && (
                            <div
                                className={cn(
                                    "grid h-10 w-10 place-items-center rounded-2xl border border-amber-100 bg-amber-50 text-amber-900",
                                    active && "ring-1 ring-amber-200"
                                )}
                            >
                                <span className="text-sm font-black">{index + 1}</span>
                            </div>
                        )}
                        <div className="min-w-0">
                            <CardTitle className="truncate font-serif text-xl text-stone-900">{step.title}</CardTitle>
                            <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-400">~{step.minutes} min</p>
                        </div>
                    </div>
                    {showBadge && (
                        <Badge className="rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
                            Step
                        </Badge>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="space-y-2">
                    {step.bullets.map((b, i) => {
                        const key = `${index}:${i}`;
                        const checked = Boolean(checks[key]);
                        return (
                            <button
                                key={key}
                                type="button"
                                onClick={() => onToggle(key)}
                                data-testid={`bullet-check-${index}-${i}`}
                                className={cn(
                                    "flex w-full items-start gap-3 rounded-2xl border border-stone-100 bg-stone-50/70 p-3 text-left",
                                    checked && "border-amber-200 bg-amber-50/50"
                                )}
                            >
                                <div
                                    className={cn(
                                        "mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-xl border border-stone-200 bg-white",
                                        checked && "border-amber-300 bg-amber-100/70"
                                    )}
                                >
                                    {checked ? <CheckCircle2 className="h-4 w-4 text-amber-700" /> : null}
                                </div>
                                <div className={cn("text-sm font-semibold", checked ? "text-stone-700" : "text-stone-800")}>
                                    {b}
                                </div>
                            </button>
                        );
                    })}
                </div>

                {step.tip && (
                    <div className="rounded-2xl border border-amber-100 bg-amber-50/60 p-4">
                        <div className="text-[10px] font-black uppercase tracking-widest text-amber-800">Chef tip</div>
                        <div className="mt-1 text-sm font-semibold text-stone-800">{step.tip}</div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// --- CookTimelineItem Component ---
function CookTimelineItem({
    step,
    index,
    isActive,
    isDone,
    isLast,
    onSelect,
    checks,
    onToggle,
    sessionId,
}: {
    step: CookStep;
    index: number;
    isActive: boolean;
    isDone: boolean;
    isLast: boolean;
    onSelect: () => void;
    checks: Record<string, boolean>;
    onToggle: (key: string) => void;
    sessionId?: string | null;
}) {
    return (
        <div className="grid grid-cols-[28px_1fr] gap-4">
            <div className="relative flex justify-center">
                {!isLast && <div className="absolute top-9 bottom-0 w-px bg-amber-300/70" />}
                <button
                    type="button"
                    onClick={onSelect}
                    className={cn(
                        "mt-1 grid h-7 w-7 place-items-center rounded-2xl border text-[11px] font-black",
                        isDone
                            ? "border-amber-400 bg-amber-500 text-white"
                            : isActive
                                ? "border-amber-300 bg-amber-100 text-amber-950"
                                : "border-stone-200 bg-white text-stone-600 hover:border-amber-200"
                    )}
                    aria-label={`Go to step ${index + 1}`}
                >
                    {isDone ? <CheckCircle2 className="h-4 w-4" /> : <span>{index + 1}</span>}
                </button>
            </div>

            <div className="text-left">
                <StepCard
                    step={step}
                    index={index}
                    active={isActive}
                    checks={checks}
                    onToggle={onToggle}
                    showIndex={false}
                    showBadge={false}
                />
                
                {isActive && sessionId && (
                    <div className="fade-in zoom-in slide-in-from-top-1 animate-in duration-300">
                        <AdjustButtons sessionId={sessionId} stepIndex={index} />
                    </div>
                )}
            </div>
        </div>
    );
}

// --- CookModeOverlay Component ---
function CookModeOverlay({
    open,
    onClose,
    recipe,
    steps,
    stepIdx,
    setStepIdx,
    checks,
    onToggle,
    onSubstitute,
    session,
    onTimerCreate,
    onTimerAction,
    onSessionEnd,
    onServingsChange,
}: {
    open: boolean;
    onClose: () => void;
    recipe: Recipe;
    steps: CookStep[];
    stepIdx: number;
    setStepIdx: (n: number) => void;
    checks: Record<string, boolean>;
    onToggle: (key: string) => void;
    onSubstitute: () => void;
    session?: CookSession | null;
    onTimerCreate?: (label: string, durationSec: number) => void;
    onTimerAction?: (timerId: string, action: 'start' | 'pause' | 'done' | 'delete') => void;
    onSessionEnd?: (action: 'complete' | 'abandon') => void;
    onServingsChange?: (target: number) => void;
}) {

    const [showAbandonConfirm, setShowAbandonConfirm] = useState(false);
    const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);
    const [activeTab, setActiveTab] = useState<'steps' | 'ingredients'>('steps');

    // Use overrides if available
    // Use overrides if available and map to CookStep format (backend uses minutes_est)
    const activeSteps = session?.steps_override
        ? (session.steps_override as any[]).map((s) => ({
            title: s.title,
            minutes: s.minutes_est ?? s.minutes ?? 5,
            bullets: s.bullets ?? [],
            tip: s.tip
        }))
        : steps;

    const handleComplete = async () => {
        // ... (confetti logic) ...
        const confettiModule = await import('@/lib/confetti.js');
        const confetti = confettiModule.default || confettiModule;

        const end = Date.now() + 1000;
        const colors = ['#f59e0b', '#d97706', '#fbbf24']; // Amber/Gold scheme

        (function frame() {
            confetti({
                particleCount: 3,
                angle: 60,
                spread: 55,
                origin: { x: 0 },
                colors: colors
            });
            confetti({
                particleCount: 3,
                angle: 120,
                spread: 55,
                origin: { x: 1 },
                colors: colors
            });

            if (Date.now() < end) {
                requestAnimationFrame(frame);
            }
        }());

        // Complete session
        onSessionEnd?.('complete');
        setShowCompleteConfirm(false);
    };
    const progress = activeSteps.length > 1 ? Math.round(((stepIdx + 1) / activeSteps.length) * 100) : 0;

    return (
        <AnimatePresence>
            {open && (
                <motion.div
                    className="fixed inset-0 z-[120] flex flex-col bg-[#FAF9F6]"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    {/* ... (loader logic) ... */}
                    {!session && (
                        <div className="absolute inset-0 z-[150] flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm">
                            <Loader2 className="h-10 w-10 animate-spin text-amber-500" />
                            <p className="mt-4 text-sm font-bold text-stone-500 uppercase tracking-widest">Starting Session...</p>
                            <button
                                onClick={onClose}
                                className="mt-8 text-xs text-stone-400 hover:text-stone-600 underline"
                            >
                                Cancel
                            </button>
                        </div>
                    )}

                    {/* amber wash */}
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-amber-50/70 via-transparent to-transparent" />

                    {/* header */}
                    <div className="relative px-6 pt-6">
                        <div className="flex items-center justify-between">
                            <button
                                type="button"
                                onClick={onClose}
                                className="rounded-2xl border border-amber-100 bg-white/80 p-3 text-stone-700 shadow-sm"
                                aria-label="Exit cook mode"
                            >
                                <X className="h-5 w-5" />
                            </button>

                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-9 rounded-xl border-red-200 text-red-600 hover:bg-red-50"
                                    onClick={() => setShowAbandonConfirm(true)}
                                >
                                    Abandon
                                </Button>
                                <Button
                                    size="sm"
                                    className="h-9 rounded-xl bg-green-600 hover:bg-green-700"
                                    onClick={() => setShowCompleteConfirm(true)}
                                >
                                    <Check className="h-4 w-4 mr-1" />
                                    Complete
                                </Button>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge className="rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
                                    Cook Mode
                                </Badge>

                                {session && (
                                    <MethodSwitcher
                                        sessionId={session.id}
                                        activeMethodKey={session.method_key}
                                    />
                                )}

                                {/* Servings Control */}
                                <div className="flex items-center gap-1 rounded-full bg-white px-1.5 py-0.5 shadow-sm border border-stone-100">
                                    <button
                                        onClick={() => onServingsChange?.(Math.max(1, (session?.servings_target || 1) - 1))}
                                        className="h-6 w-6 grid place-items-center rounded-full hover:bg-stone-50 text-stone-400 hover:text-stone-600 transition-colors"
                                    >
                                        <Minus className="h-3 w-3" />
                                    </button>
                                    <span className="text-xs font-bold text-stone-700 w-4 text-center">
                                        {session?.servings_target || recipe.servings || 1}
                                    </span>
                                    <button
                                        onClick={() => onServingsChange?.((session?.servings_target || 1) + 1)}
                                        className="h-6 w-6 grid place-items-center rounded-full hover:bg-stone-50 text-stone-400 hover:text-stone-600 transition-colors"
                                    >
                                        <Plus className="h-3 w-3" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="mt-4 overflow-hidden rounded-[2.5rem] border border-amber-100/50 bg-white shadow-sm">
                            <div className="relative h-[180px] w-full bg-amber-50">
                                {recipe.primary_image_url ? (
                                    <img
                                        src={recipe.primary_image_url}
                                        alt={recipe.title}
                                        className="h-full w-full object-cover"
                                    />
                                ) : (
                                    <div className="h-full w-full flex items-center justify-center">
                                        <ChefHat className="h-16 w-16 text-amber-200" />
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />
                                <div className="absolute bottom-4 left-4 right-4">
                                    <div className="font-serif text-2xl leading-tight text-white">{recipe.title}</div>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        <span className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                                            Progress {progress}%
                                        </span>
                                        {recipe.cuisines?.slice(0, 2).map((c) => (
                                            <span key={c} className="rounded-lg border border-white/20 bg-white/20 px-2.5 py-1 text-[9px] font-black uppercase tracking-widest text-white backdrop-blur-md">
                                                {c}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* tabs & content */}
                    <div className="relative flex-1 overflow-y-auto px-6 pb-28 pt-6 no-scrollbar">
                        {/* Tab Switcher */}
                        <div className="sticky top-0 z-10 -mx-6 mb-4 bg-gradient-to-b from-[#FAF9F6] via-[#FAF9F6]/90 to-transparent px-6 pb-3 pt-2">
                            <div className="flex items-center gap-1 p-1 rounded-xl bg-stone-200/50 mb-4">
                                <button
                                    onClick={() => setActiveTab('steps')}
                                    className={cn(
                                        "flex-1 py-2 text-xs font-black uppercase tracking-widest rounded-lg transition-all",
                                        activeTab === 'steps' ? "bg-white shadow-sm text-stone-900" : "text-stone-500 hover:text-stone-700"
                                    )}
                                >
                                    Steps
                                </button>
                                <button
                                    onClick={() => setActiveTab('ingredients')}
                                    className={cn(
                                        "flex-1 py-2 text-xs font-black uppercase tracking-widest rounded-lg transition-all",
                                        activeTab === 'ingredients' ? "bg-white shadow-sm text-stone-900" : "text-stone-500 hover:text-stone-700"
                                    )}
                                >
                                    Ingredients
                                </button>
                            </div>

                            {activeTab === 'steps' && (
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-stone-600">
                                        <span className="inline-flex h-2 w-2 rounded-full bg-amber-500" />
                                        Step timeline
                                    </div>
                                    <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-stone-500">
                                        Tap a node
                                        <ChevronRight className="h-4 w-4 rotate-90 text-amber-700" />
                                    </div>
                                </div>
                            )}
                        </div>

                        {activeTab === 'steps' ? (
                            <div className="space-y-5">
                                {activeSteps.map((s, i) => {
                                    const done = s.bullets.every((_: any, bi: number) => Boolean(checks[`${i}:${bi}`]));
                                    return (
                                        <CookTimelineItem
                                            key={`${s.title}-${i}`}
                                            step={s}
                                            index={i}
                                            isActive={i === stepIdx}
                                            isDone={done}
                                            isLast={i === activeSteps.length - 1}
                                            onSelect={() => setStepIdx(i)}
                                            checks={checks}
                                            onToggle={onToggle}
                                            sessionId={session?.id}
                                        />
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <IngredientsView
                                    ingredients={recipe.ingredients}
                                    baseServings={session?.servings_base || recipe.servings || 1}
                                    targetServings={session?.servings_target || recipe.servings || 1}
                                />
                            </div>
                        )}


                        <div className="mt-6 space-y-4">
                            {/* Timer Manager */}
                            <Card className="rounded-[2.5rem] border-amber-100/50 bg-white shadow-sm">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-sm text-stone-900 flex items-center gap-2">
                                        <Clock className="h-4 w-4 text-amber-600" />
                                        Timers
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <TimerManager
                                        stepIndex={stepIdx}
                                        timers={session?.timers || {}}
                                        onTimerCreate={(label, durationSec) => {
                                            onTimerCreate?.(label, durationSec);
                                        }}
                                        onTimerAction={(timerId, action) => {
                                            onTimerAction?.(timerId, action);
                                        }}
                                    />
                                </CardContent>
                            </Card>

                            {/* Sticky Cooking Assist Button */}
                            {open && (
                                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[125] shadow-2xl">
                                    <AssistPanel recipeId={recipe.id} stepIndex={stepIdx} />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* bottom controls */}
                    <div className="fixed bottom-0 left-0 right-0 z-[130] border-t border-amber-100/60 bg-white/90 px-6 pb-6 pt-4 backdrop-blur-2xl">
                        <div className="mb-3 flex items-center justify-between">
                            <div className="text-[10px] font-black uppercase tracking-widest text-stone-500">
                                Step {Math.min(stepIdx + 1, activeSteps.length)} of {activeSteps.length}
                            </div>
                            <div className="text-[10px] font-black uppercase tracking-widest text-amber-800">{activeSteps[stepIdx]?.minutes ?? 0} min</div>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                variant="outline"
                                className="h-12 flex-1 rounded-2xl border-amber-100/60 hover:bg-amber-50/60"
                                onClick={() => setStepIdx(Math.max(0, stepIdx - 1))}
                                disabled={stepIdx === 0}
                            >
                                Previous
                            </Button>
                            <Button
                                className="h-12 flex-1 rounded-2xl bg-stone-900 text-xs font-black uppercase tracking-widest text-white hover:bg-stone-900"
                                onClick={() => setStepIdx(Math.min(activeSteps.length - 1, stepIdx + 1))}
                                disabled={stepIdx >= activeSteps.length - 1}
                            >
                                Next
                            </Button>
                        </div>
                    </div>

                    {/* Abandon Confirmation Dialog */}
                    <AlertDialog open={showAbandonConfirm} onOpenChange={setShowAbandonConfirm}>
                        <AlertDialogContent className="z-[130]">
                            <AlertDialogHeader>
                                <AlertDialogTitle>Abandon Cooking Session?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    This will end your cooking session and mark it as abandoned. Your progress will be saved but you'll need to start a new session to continue.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={() => {
                                    onSessionEnd?.('abandon');
                                    setShowAbandonConfirm(false);
                                }}>
                                    Abandon Session
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>

                    {/* Completion Confirmation Dialog */}
                    <AlertDialog open={showCompleteConfirm} onOpenChange={setShowCompleteConfirm}>
                        <AlertDialogContent className="z-[130]">
                            <AlertDialogHeader>
                                <AlertDialogTitle className="text-center font-serif text-2xl text-amber-900">Bon Appétit!</AlertDialogTitle>
                                <AlertDialogDescription className="text-center">
                                    Congratulations on finishing your meal! Would you like to mark this session as complete?
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter className="sm:justify-center gap-2">
                                <AlertDialogCancel className="rounded-xl">Keep Cooking</AlertDialogCancel>
                                <AlertDialogAction
                                    className="bg-green-600 hover:bg-green-700 text-white rounded-xl px-8"
                                    onClick={handleComplete}
                                >
                                    Yes, Complete!
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// --- RecipeHero Component ---
function RecipeHero({ recipe }: { recipe: Recipe }) {
    const queryClient = useQueryClient();

    // Image status polling
    const { data: imageStatus } = useImageStatus(recipe.id, {
        refetchInterval: 2000,
    });

    // Mutations
    const generateImageMutation = useGenerateImage();
    const regenerateImageMutation = useRegenerateImage();

    const isGenerating = imageStatus?.status === 'pending' || imageStatus?.status === 'processing';
    const activeImageUrl = imageStatus?.status === 'ready' && imageStatus.public_url
        ? imageStatus.public_url
        : recipe.primary_image_url;

    const handleGenerate = () => {
        generateImageMutation.mutate(recipe.id);
    };

    const handleRegenerate = () => {
        regenerateImageMutation.mutate(recipe.id);
    };

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

                {/* Generate/Regenerate UI */}
                <div className="absolute top-4 right-4 z-20">
                    {/* Regenerate Button (only if image exists and not generating) */}
                    {activeImageUrl && !isGenerating && (
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
                            className="h-12 gap-2 rounded-full border border-amber-200/50 bg-white/90 px-6 text-stone-800 shadow-xl backdrop-blur-sm hover:bg-white"
                        >
                            <Sparkles className="h-4 w-4 text-amber-500" />
                            <span className="font-bold text-xs uppercase tracking-widest">Generate Image</span>
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
                    <h1 className="font-serif text-3xl leading-tight text-white drop-shadow-md">{recipe.title}</h1>
                    <div className="mt-3 flex flex-wrap gap-2">
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
                    {recipe.time_minutes && (
                        <div className="flex items-center gap-2">
                            <Clock className="h-4 w-4 text-amber-600" />
                            <span className="font-semibold">{recipe.time_minutes} min</span>
                        </div>
                    )}
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

                {recipe.notes && (
                    <p className="mt-4 text-sm text-stone-600 leading-relaxed">{recipe.notes}</p>
                )}
            </div>
        </div>
    );
}


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

// --- Main Page Component ---
export default function RecipeDetailPage() {
    const params = useParams();
    const router = useRouter();
    const recipeId = params.id as string;
    const queryClient = useQueryClient(); // Fix: Define queryClient

    const { data: recipe, isLoading, error } = useRecipe(recipeId);

    // Cook mode state
    const [cookOpen, setCookOpen] = useState(false);
    const [subOpen, setSubOpen] = useState(false);
    const [stepIdx, setStepIdx] = useState(0);

    // Cook session hooks
    const { data: session, isLoading: sessionLoading } = useCookSessionActive(recipeId);
    const startSessionMutation = useCookSessionStart();
    const patchSessionMutation = useCookSessionPatch();
    const endSessionMutation = useCookSessionEnd();
    const startGuardRef = useRef(false);
    const wantCookRef = useRef(false); // User intent: wants cook mode open

    // Start Cooking Handler
    const handleStartCooking = () => {
        wantCookRef.current = true;
        // Ensure we don't have stale "no session" or "old session" data
        queryClient.removeQueries({ queryKey: ['cook-session', 'active', recipeId] });
        setCookOpen(true);
    };

    // Auto-start session when cook mode opens
    useEffect(() => {
        // Only run when the user actually wants to cook
        if (!wantCookRef.current) return;
        if (!cookOpen) return;
        if (sessionLoading) return;

        // If we already have a session, stop.
        if (session) {
            return;
        }

        // Prevent strict-mode double fire
        if (startGuardRef.current) return;
        startGuardRef.current = true;

        startSessionMutation.mutate(recipeId, {
            onError: (e) => {
                console.error('[CookMode] Start failed:', e);
                startGuardRef.current = false;
            },
            onSettled: () => {
                startGuardRef.current = false;
            }
        });
    }, [cookOpen, sessionLoading, session, recipeId, startSessionMutation]);

    // Reset guards when cook mode closes
    useEffect(() => {
        if (!cookOpen) {
            startGuardRef.current = false;
            // potential: wantCookRef.current = false; // logic handled in abandon
        }
    }, [cookOpen]);

    // Update step index from session
    // Only sync if we're not currently patching (avoids race condition/oscillation)
    useEffect(() => {
        if (session && cookOpen && !patchSessionMutation.isPending) {

            setStepIdx(session.current_step_index);
        }
    }, [session, cookOpen, patchSessionMutation.isPending]);

    // Sync step index to session when changed
    const handleStepChange = (newStepIdx: number) => {


        setStepIdx(newStepIdx);
        if (session) {
            patchSessionMutation.mutate({
                sessionId: session.id, // Pass sessionId
                patch: {
                    current_step_index: newStepIdx
                }
            });
        }
    };

    // Get checks from session or empty object
    const checks: Record<string, boolean> = {};
    if (session) {
        Object.entries(session.step_checks).forEach(([stepIdx, bullets]) => {
            Object.entries(bullets).forEach(([bulletIdx, checked]) => {
                if (checked) {
                    checks[`${stepIdx}:${bulletIdx}`] = true;
                }
            });
        });
    }

    // Subscribe to real-time events
    useCookSessionEvents(session?.id);

    const toggleCheck = (key: string) => {
        const [stepIndex, bulletIndex] = key.split(':').map(Number);
        const checked = !checks[key];

        if (session) {
            patchSessionMutation.mutate({
                sessionId: session.id, // Pass sessionId
                patch: {
                    step_checks_patch: {
                        step_index: stepIndex,
                        bullet_index: bulletIndex,
                        checked,
                    },
                }
            });
        }
    };

    const handleServingsChange = (target: number) => {
        if (session) {
            // Optimistic update handled by cache or wait for response?
            // Mutation will settle and refetch/update cache.
            // SSE will also push update.
            patchSessionMutation.mutate({
                sessionId: session.id,
                patch: { servings_target: target }
            });
        }
    }

    // Handle session end
    const handleSessionEnd = (action: 'complete' | 'abandon') => {
        console.log('[CookMode] handleSessionEnd called:', action);
        // User explicitly ending session -> Clear intent
        wantCookRef.current = false;

        if (!session) {
            console.log('[CookMode] No session active, ignoring');
            setCookOpen(false);
            return;
        }
        console.log('[CookMode] Mutating session end...', session.id);
        endSessionMutation.mutate(
            { sessionId: session.id, action },
            {
                onSuccess: () => {
                    console.log('[CookMode] Session end success, closing cook mode');
                    setCookOpen(false);
                    setStepIdx(0); // Reset local step index
                    // Invalidate active session query so next time it fetches fresh (or null)
                    queryClient.invalidateQueries({ queryKey: ['cook-session', 'active', recipeId] });
                },
                onError: (e) => {
                    console.error('[CookMode] Session end failed:', e);
                    // Force close anyway on abandon error to prevent getting stuck
                    if (action === 'abandon') setCookOpen(false);
                }
            }
        );
    };

    // Convert API steps to CookStep format
    const cookSteps: CookStep[] = recipe?.steps.map(apiStepToCookStep) ?? [];


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

    return (
        <div className="min-h-screen bg-[#FAF9F6]">
            {/* Subtle amber wash */}
            <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-amber-50/60 via-transparent to-transparent" />

            {/* Cook Mode Overlay */}
            <CookModeOverlay
                open={cookOpen}
                onClose={() => setCookOpen(false)}
                recipe={recipe}
                steps={cookSteps}
                stepIdx={stepIdx}
                setStepIdx={handleStepChange}
                checks={checks}
                onToggle={toggleCheck}
                onSubstitute={() => setSubOpen(true)}
                session={session}
                onServingsChange={handleServingsChange}
                onTimerCreate={(label, durationSec) => {
                    if (session) {
                        patchSessionMutation.mutate({
                            sessionId: session.id, // Pass sessionId
                            patch: {
                                timer_create: {
                                    step_index: stepIdx,
                                    bullet_index: null,
                                    label,
                                    duration_sec: durationSec,
                                },
                            }
                        });
                    }
                }}
                onTimerAction={(timerId, action) => {
                    if (session) {
                        patchSessionMutation.mutate({
                            sessionId: session.id, // Pass sessionId
                            patch: {
                                timer_action: { timer_id: timerId, action },
                            }
                        });
                    }
                }}
                onSessionEnd={handleSessionEnd}
            />

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

                    <ShareRecipeModal recipeId={recipeId} />
                </div>

                {/* Hero */}
                <RecipeHero recipe={recipe} />

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
                                        <p className="font-bold text-stone-900">{step.title}</p>
                                        <p className="text-[10px] font-black uppercase tracking-widest text-stone-400">~{step.minutes} min</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {cookSteps.length > 3 && (
                            <p className="text-center text-sm text-stone-400">+{cookSteps.length - 3} more steps</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Floating Start Cook Mode Button */}
            <div className="fixed bottom-6 left-0 right-0 px-6 z-40">
                <div className="mx-auto max-w-2xl">
                    <button
                        type="button"
                        onClick={handleStartCooking}
                        className="flex w-full items-center justify-center gap-3 rounded-[2rem] bg-stone-900 py-5 text-xs font-black uppercase tracking-[0.3em] text-white shadow-2xl transition-all active:scale-95 hover:bg-stone-800"
                    >
                        <Flame className="h-5 w-5 text-amber-400" />
                        Start Cook Mode
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
