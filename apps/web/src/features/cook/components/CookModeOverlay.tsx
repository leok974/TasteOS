'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { IngredientRow } from "@/features/recipes/components/IngredientRow";
import { cleanTitle } from '@/lib/recipeSanitize';
import {
    X,
    Sparkles,
    Check,
    Minus,
    Plus,
    ScrollText,
    RotateCcw,
    Loader2,
    ChefHat,
    ChevronRight,
    CheckCircle2,
    Clock
} from 'lucide-react';
import { cn } from '@/lib/cn';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
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
import { useSWRConfig } from 'swr';
import type { Recipe } from '@/lib/api';
import {
    useCookSessionEvents,
    useCookAdjustmentUndo,
    CookSession,
    CookTimer,
} from '@/features/cook/hooks';
import { MethodSwitcher } from '@/features/cook/MethodSwitcher';
import { AdjustButtons } from '@/features/cook/AdjustButtons';
import { StepHelpDrawer } from './StepHelpDrawer';
import { WhyPanel } from '@/features/cook/components/WhyPanel';
import { TimerSuggestions } from '@/features/cook/components/TimerSuggestions';
import { SessionSummary } from '@/features/cook/SessionSummary';
import { ResumeBanner } from '@/features/cook/components/ResumeBanner';
import { TimerDock } from '@/features/cook/components/TimerDock';
import { NextUpPanel } from './NextUpPanel';
import { apiPatchSession } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// --- Types ---

export interface CookStep {
    title: string;
    minutes: number;
    bullets: string[];
    tip?: string;
}

// --- Helpers ---

type SwitchProps = {
    checked: boolean;
    onCheckedChange: (checked: boolean) => void;
};

function Switch({ checked, onCheckedChange }: SwitchProps) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            onClick={() => onCheckedChange(!checked)}
            className={cn(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2",
                checked ? "bg-amber-500" : "bg-stone-200"
            )}
        >
            <span
                className={cn(
                    "pointer-events-none block h-5 w-5 rounded-full bg-white shadow-lg ring-0 transition-transform",
                    checked ? "translate-x-5" : "translate-x-0"
                )}
            />
        </button>
    );
}

// Re-using StepCard from page.tsx (duplicated for now to avoid circular deps if StepCard stays in page.tsx)
// Ideally this should be shared.
function StepCard({
    step,
    index,
    active,
    checks,
    onToggle,
    onTimerCreate,
    showIndex = true,
    showBadge = true,
    onHelpClick, // New prop
}: {
    step: CookStep;
    index: number;
    active: boolean;
    checks: Record<string, boolean>;
    onToggle: (key: string) => void;
    onTimerCreate?: (stepIndex: number, label: string, durationSec: number) => void;
    showIndex?: boolean;
    showBadge?: boolean;
    onHelpClick?: () => void;
}) {
    const handleStartTimer = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (onTimerCreate && step.minutes) {
            onTimerCreate(index, step.title, step.minutes * 60);
        }
    };

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
                            <div className="text-lg font-semibold leading-snug line-clamp-2 text-stone-900">{step.title}</div>
                            <p className="mt-1 text-[10px] font-black uppercase tracking-widest text-stone-400">~{step.minutes} min</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Help Button (v15.2) */}
                        {onHelpClick && (
                             <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 w-8 rounded-full p-0 text-amber-700 hover:bg-amber-100"
                                onClick={(e) => { e.stopPropagation(); onHelpClick(); }}
                                aria-label="Ask about this step"
                            >
                                <Sparkles className="h-4 w-4" />
                            </Button>
                        )}
                        
                        {step.minutes > 0 && onTimerCreate && (
                            <button
                                onClick={handleStartTimer}
                                className="flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-900 transition-colors hover:bg-amber-100"
                            >
                                <Clock className="w-3 h-3" />
                                <span>{step.minutes}m</span>
                            </button>
                        )}
                        {showBadge && (
                            <Badge className="rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
                                Step
                            </Badge>
                        )}
                    </div>
                </div>
            </CardHeader>

            <CardContent className="space-y-3">
                <div className="space-y-1">
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
                                    "flex w-full items-start gap-3 rounded-2xl border border-stone-100 bg-stone-50/70 p-2.5 text-left transition-colors",
                                    checked && "border-amber-200 bg-amber-50/50"
                                )}
                            >
                                <div
                                    className={cn(
                                        "mt-1 grid h-5 w-5 flex-none place-items-center rounded-full border border-stone-200 bg-white",
                                        checked && "border-amber-300 bg-amber-100/70"
                                    )}
                                >
                                    {checked ? <CheckCircle2 className="h-3.5 w-3.5 text-amber-700" /> : null}
                                </div>
                                <div className={cn("min-w-0 flex-1 whitespace-normal break-words text-sm leading-snug", checked ? "text-stone-500 line-through decoration-stone-300" : "text-stone-600")}>
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

function CookTimelineItem({
    step,
    index,
    isActive,
    isDone,
    isLast,
    onSelect,
    checks,
    onToggle,
    onTimerCreate,
    sessionId,
    activeTimers,
    onHelpClick, // Added prop
}: {
    step: CookStep;
    index: number;
    isActive: boolean;
    isDone: boolean;
    isLast: boolean;
    onSelect: () => void;
    checks: Record<string, boolean>;
    onToggle: (key: string) => void;
    onTimerCreate?: (stepIndex: number, label: string, durationSec: number) => void;
    sessionId?: string | null;
    activeTimers?: Record<string, CookTimer>;
    onHelpClick?: () => void;
}) {
    const itemRef = useRef<HTMLDivElement>(null);

    // Auto-scroll when active
    useEffect(() => {
        if (isActive && itemRef.current) {
            itemRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, [isActive]);

    return (
        <div ref={itemRef} className="grid grid-cols-[28px_1fr] gap-4 scroll-mt-24">
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
                    onTimerCreate={onTimerCreate}
                    showIndex={false}
                    showBadge={false}
                    onHelpClick={isActive ? onHelpClick : undefined}
                />

                {isActive && sessionId && (
                    <div className="fade-in zoom-in slide-in-from-top-1 animate-in duration-300">
                        {activeTimers && (
                            <TimerSuggestions 
                                sessionId={sessionId} 
                                stepIndex={index} 
                                activeTimers={activeTimers} 
                            />
                        )}
                        <AdjustButtons sessionId={sessionId} stepIndex={index} />
                    </div>
                )}
            </div>
        </div>
    );
}

// --- Main Component ---

export function CookModeOverlay({
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
    sessionRefetching = false,
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
    sessionRefetching?: boolean;
    onTimerCreate?: (stepIndex: number, label: string, durationSec: number) => void;
    onTimerAction?: (timerId: string, action: 'start' | 'pause' | 'done' | 'delete') => void;
    onSessionEnd?: (action: 'complete' | 'abandon') => void;
    onServingsChange?: (target: number) => void;
}) {
    const { mutate } = useSWRConfig();
    const [showAbandonConfirm, setShowAbandonConfirm] = useState(false);
    const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);
    const [summaryId, setSummaryId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'steps' | 'ingredients'>('steps');

    // V15.2 Step Help
    const [helpTargetIndex, setHelpTargetIndex] = useState<number | null>(null);

    // V13 States
    const [isHandsFree, setIsHandsFree] = useState(false);

    // Resume Banner Logic (Robust)
    const [bannerDismissed, setBannerDismissed] = useState(false);
    const [sessionInitialLoad, setSessionInitialLoad] = useState(false);

    // Reset state when session ID changes (new session)
    useEffect(() => {
        if (session?.id) {
            setBannerDismissed(false);
            setSessionInitialLoad(false);
        }
    }, [session?.id]);

    // Check initial state once per session load
    useEffect(() => {
        if (session && !sessionInitialLoad) {
            // Wait for refetch to complete before deciding to auto-dismiss
            // This prevents stale cache (Step 0) from hiding the banner if server has progress
            if (sessionRefetching) return; 

            // If we load an existing session with progress, allow banner.
            // If we load a new session (step 0), effectively dismiss it immediately.
            if (session.current_step_index > 0 && !session.ended_at) {
                setBannerDismissed(false);
            } else {
                setBannerDismissed(true);
            }
            setSessionInitialLoad(true);
        }
    }, [session, sessionInitialLoad, sessionRefetching]);

    const showResumeBanner = session &&
        !session.ended_at &&
        session.current_step_index > 0 &&
        !bannerDismissed &&
        sessionInitialLoad;


    // Wake Lock for Hands Free
    useEffect(() => {
        let wakeLock: any = null;
        if (isHandsFree && 'wakeLock' in navigator) {
            const requestLock = async () => {
                try {
                    wakeLock = await (navigator as any).wakeLock.request('screen');
                } catch (err) {
                    console.log('Wake Lock failed', err);
                }
            };
            requestLock();
        }
        return () => {
            if (wakeLock) wakeLock.release();
        };
    }, [isHandsFree]);

    // Sync hands_free state from session if available (optional)
    useEffect(() => {
        if (session?.hands_free?.enabled) {
            setIsHandsFree(true);
        }
    }, [session?.hands_free]);

    const { undoAdjustment, isUndoing } = useCookAdjustmentUndo(session?.id);

    // Calculate if we can undo (any adjustment in log that isn't undone)
    const canUndo = useMemo(() => {
        if (!session?.adjustments_log?.length) return false;
        return session.adjustments_log.some((adj: any) => !adj.undone);
    }, [session?.adjustments_log]);

    // Sync external step index changes (e.g. from Auto-Jump or other devices)
    useEffect(() => {
        if (session?.current_step_index != null && session.current_step_index !== stepIdx) {
            setStepIdx(session.current_step_index);
        }
    }, [session?.current_step_index, stepIdx, setStepIdx]);

    const handleAutoStepToggle = async (enabled: boolean) => {
        if (!session) return;
        await apiPatchSession(session.id, { auto_step_enabled: enabled });
        mutate(`/api/cook/session/${session.id}`);
    };

    const handleAutoModeToggle = async () => {
        if (!session) return;
        const newMode = session.auto_step_mode === 'auto_jump' ? 'suggest' : 'auto_jump';
        await apiPatchSession(session.id, { auto_step_mode: newMode });
        mutate(`/api/cook/session/${session.id}`);
    };

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
        if (session) {
            setSummaryId(session.id);
        }
        onSessionEnd?.('complete');
        setShowCompleteConfirm(false);
    };
    const progress = activeSteps.length > 1 ? Math.round(((stepIdx + 1) / activeSteps.length) * 100) : 0;

    // --- Ingredients Helper for Overlay ---
    // --- Ingredient Logic ---




    function OverlayIngredients({
        ingredients,
        baseServings,
        targetServings
    }: {
        ingredients: Recipe['ingredients'];
        baseServings: number;
        targetServings: number;
    }) {
        const [mode, setMode] = useState<'default' | 'metric' | 'imperial'>('default');

        if (!ingredients || ingredients.length === 0) {
            return (
                <div className="flex flex-col items-center justify-center p-8 text-center bg-stone-50/50 rounded-2xl border border-stone-100">
                    <p className="text-stone-400 text-sm font-medium">No ingredients listed</p>
                </div>
            );
        }

        const factor = targetServings / (baseServings || 1);

        return (
            <div className="space-y-4">
                 <div className="flex justify-between items-center px-1">
                     <span className="text-[10px] font-black uppercase tracking-[0.2em] text-stone-400">Ingredients</span>
                     <div className="flex bg-stone-100 rounded-lg p-1">
                         <button onClick={() => setMode('default')} className={cn("px-2 py-1 text-[10px] uppercase font-bold rounded-md transition-colors", mode === 'default' ? "bg-white shadow-sm text-stone-900" : "text-stone-400 hover:text-stone-600")}>Orig</button>
                         <button onClick={() => setMode('metric')} className={cn("px-2 py-1 text-[10px] uppercase font-bold rounded-md transition-colors", mode === 'metric' ? "bg-white shadow-sm text-stone-900" : "text-stone-400 hover:text-stone-600")}>Metric</button>
                         <button onClick={() => setMode('imperial')} className={cn("px-2 py-1 text-[10px] uppercase font-bold rounded-md transition-colors", mode === 'imperial' ? "bg-white shadow-sm text-stone-900" : "text-stone-400 hover:text-stone-600")}>Imp</button>
                     </div>
                 </div>

                <div className="space-y-2">
                    {ingredients.map((ing, i) => (
                         <IngredientRow 
                            key={i} 
                            ingredient={ing} 
                            scaleFactor={factor} 
                            mode={mode} 
                        />
                    ))}
                </div>
            </div>
        );
    }

    const activeTimersCount = session
        ? Object.values(session.timers || {}).filter(t => !t.deleted_at).length
        : 0;

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
                    {!session && !summaryId && (
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

                    {summaryId && (
                        <div className="absolute inset-0 z-[160] overflow-y-auto bg-[#FAF9F6] p-4 flex items-center justify-center">
                            <div className="w-full max-w-2xl relative">
                                <button
                                    onClick={() => {
                                        setSummaryId(null);
                                        onClose();
                                    }}
                                    className="absolute md:-right-12 -right-2 -top-12 md:top-0 p-2 text-stone-500 hover:text-stone-700 bg-white/50 rounded-full"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                                <SessionSummary
                                    sessionId={summaryId}
                                    recipeId={recipe.id}
                                    onClose={() => {
                                        setSummaryId(null);
                                        onClose();
                                    }}
                                />
                            </div>
                        </div>
                    )}

                    {/* amber wash */}
                    <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-amber-50/70 via-transparent to-transparent" />

                    {/* Resume Banner */}
                    {showResumeBanner && (
                        <ResumeBanner
                            stepIndex={session!.current_step_index}
                            onResume={() => setBannerDismissed(true)}
                            onStartOver={async () => {
                                // Reset step index
                                setBannerDismissed(true); // Hide immediately
                                setStepIdx(0); // Triggers parent mutation
                            }}
                        />
                    )}

                    {/* Next Up Panel (v13.1) */}
                    {session && (
                         <NextUpPanel 
                            session={session} 
                            recipe={recipe} 
                            className={activeTimersCount > 0 
                                ? (isHandsFree ? "bottom-[196px]" : "bottom-[172px]") 
                                : (isHandsFree ? "bottom-[112px]" : "bottom-[88px]")
                            } 
                         />
                    )}

                    {/* Timer Dock */}
                    {session && (<TimerDock session={session} sessionId={session.id} className={isHandsFree ? "bottom-[112px]" : "bottom-[88px]"} />)}

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
                                {/* Hands Free Toggle */}
                                <Button
                                    size="sm"
                                    variant={isHandsFree ? "default" : "outline"}
                                    onClick={() => setIsHandsFree(!isHandsFree)}
                                    className={cn(
                                        "h-9 rounded-xl border-amber-200/50 bg-amber-50/50 text-amber-700 transition-colors",
                                        isHandsFree && "bg-amber-600 text-white hover:bg-amber-700 border-transparent"
                                    )}
                                >
                                    {isHandsFree ? "👐 Hands Free" : "👐 Off"}
                                </Button>

                                <Badge className="hidden sm:inline-flex rounded-full bg-amber-100/70 text-amber-950 hover:bg-amber-100/70" variant="secondary">
                                    Cook Mode
                                </Badge>

                                {session && (
                                    <>
                                        <div className="flex items-center gap-2 rounded-full border border-amber-100/50 bg-white/80 px-3 py-1.5 shadow-sm backdrop-blur-sm">
                                            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Auto</span>
                                            <Switch
                                                checked={session.auto_step_enabled}
                                                onCheckedChange={handleAutoStepToggle}
                                            />
                                            {session.auto_step_enabled && (
                                                <button
                                                    onClick={handleAutoModeToggle}
                                                    className="ml-1 text-[10px] uppercase font-black text-amber-600 border-l border-stone-200 pl-2 hover:text-amber-800"
                                                >
                                                    {session.auto_step_mode === 'auto_jump' ? 'Jump' : 'Suggest'}
                                                </button>
                                            )}
                                        </div>

                                        {canUndo && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => undoAdjustment()}
                                                disabled={isUndoing}
                                                className="h-[34px] rounded-full border-amber-200/50 bg-amber-50/50 hover:bg-amber-100/50 text-amber-700"
                                            >
                                                <RotateCcw className={cn("h-4 w-4 mr-1.5", isUndoing && "animate-spin")} />
                                                Undo
                                            </Button>
                                        )}

                                        <MethodSwitcher
                                            sessionId={session.id}
                                            activeMethodKey={session.method_key}
                                        />

                                        {/* History / Why Panel */}
                                        <Sheet>
                                            <SheetTrigger asChild>
                                                <Button variant="outline" size="sm" className="h-[34px] rounded-full border-amber-200/50 bg-amber-50/50 hover:bg-amber-100/50 text-amber-700">
                                                    <ScrollText className="h-4 w-4 mr-1.5" />
                                                    Why?
                                                </Button>
                                            </SheetTrigger>
                                            <SheetContent className="w-[400px] sm:w-[540px]">
                                                <SheetHeader>
                                                    <SheetTitle>Session Diagnostics</SheetTitle>
                                                    <SheetDescription>
                                                        Review the events and decisions made during this cooking session.
                                                    </SheetDescription>
                                                </SheetHeader>
                                                <div className="mt-6">
                                                    <WhyPanel sessionId={session.id} />
                                                </div>
                                            </SheetContent>
                                        </Sheet>
                                    </>
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
                                        alt={cleanTitle(recipe.title)}
                                        className="h-full w-full object-cover"
                                    />
                                ) : (
                                    <div className="h-full w-full flex items-center justify-center">
                                        <ChefHat className="h-16 w-16 text-amber-200" />
                                    </div>
                                )}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/10 to-transparent" />
                                <div className="absolute bottom-4 left-4 right-4">
                                    <div className="font-serif text-2xl leading-tight text-white">{cleanTitle(recipe.title)}</div>
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
                        {/* Auto Step Suggestion Banner */}
                        <AnimatePresence>
                            {session?.auto_step_enabled &&
                                session.auto_step_mode !== 'auto_jump' &&
                                session.auto_step_suggested_index != null &&
                                session.auto_step_suggested_index !== stepIdx && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -20, height: 0 }}
                                        animate={{ opacity: 1, y: 0, height: 'auto' }}
                                        exit={{ opacity: 0, y: -20, height: 0 }}
                                        className="mb-4 overflow-hidden"
                                    >
                                        <div className="rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-amber-100/50 p-4 shadow-sm flex items-center justify-between gap-4">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-2 text-amber-900 font-bold text-sm mb-1">
                                                    <Sparkles className="h-4 w-4 text-amber-500 fill-amber-500" />
                                                    Suggested: Step {session.auto_step_suggested_index + 1}
                                                </div>
                                                <div className="text-xs text-amber-700/80 line-clamp-1 italic">
                                                    {session.auto_step_reason ? `Because: ${session.auto_step_reason}` : "Based on recent activity"}
                                                </div>
                                            </div>
                                            <Button
                                                size="sm"
                                                className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl shadow-md whitespace-nowrap"
                                                onClick={() => setStepIdx(session.auto_step_suggested_index!)}
                                            >
                                                Jump Here
                                            </Button>
                                        </div>
                                    </motion.div>
                                )}
                        </AnimatePresence>

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
                                    const isActive = stepIdx === i;
                                    const isDone = i < stepIdx;
                                    const isLast = i === activeSteps.length - 1;

                                    return (
                                        <CookTimelineItem
                                            key={i}
                                            step={s}
                                            index={i}
                                            isActive={isActive}
                                            isDone={isDone}
                                            isLast={isLast}
                                            onSelect={() => setStepIdx(i)}
                                            checks={checks}
                                            onToggle={onToggle}
                                            onTimerCreate={onTimerCreate}
                                            sessionId={session?.id}
                                            activeTimers={session?.timers}
                                            onHelpClick={() => setHelpTargetIndex(i)}
                                        />
                                    );
                                })}
                            </div>
                        ) : (
                            <OverlayIngredients
                                ingredients={recipe.ingredients}
                                baseServings={session?.servings_base || recipe.servings || 1}
                                targetServings={session?.servings_target || recipe.servings || 1}
                            />
                        )}
                    </div>

                    {/* Bottom Controls */}
                    <div className="bg-[#FAF9F6] border-t border-stone-100 p-6 z-[130]">
                        {/* Hands Free Nav */}
                        {isHandsFree ? (
                            <div className="flex gap-4">
                                <Button
                                    variant="outline"
                                    size="lg"
                                    className="flex-1 h-16 rounded-2xl border-2 border-stone-200 text-lg font-bold hover:bg-stone-50 text-stone-600"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setStepIdx(Math.max(0, stepIdx - 1));
                                    }}
                                    disabled={stepIdx === 0}
                                >
                                    Previous
                                </Button>
                                <Button
                                    size="lg"
                                    className="flex-1 h-16 rounded-2xl bg-amber-500 hover:bg-amber-600 text-white text-lg font-bold shadow-xl shadow-amber-200/50"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        if (stepIdx < activeSteps.length - 1) {
                                            setStepIdx(stepIdx + 1);
                                        } else {
                                            setShowCompleteConfirm(true);
                                        }
                                    }}
                                >
                                    {stepIdx === activeSteps.length - 1 ? "Finish!" : "Next Step"}
                                </Button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-4">
                                <Button
                                    variant="outline"
                                    className="flex-1 h-12 rounded-2xl bg-white border-stone-200 hover:bg-stone-50 text-stone-600 font-bold"
                                    onClick={() => setStepIdx(Math.max(0, stepIdx - 1))}
                                    disabled={stepIdx === 0}
                                >
                                    Back
                                </Button>
                                <Button
                                    className="flex-[2] h-12 rounded-2xl bg-amber-500 hover:bg-amber-600 text-white font-bold shadow-lg shadow-amber-200/50"
                                    onClick={() => {
                                        if (stepIdx < activeSteps.length - 1) {
                                            setStepIdx(stepIdx + 1);
                                        } else {
                                            setShowCompleteConfirm(true);
                                        }
                                    }}
                                >
                                    {stepIdx === activeSteps.length - 1 ? "Finish Cooking" : "Next Step"}
                                </Button>
                            </div>
                        )}
                    </div>

                    {/* Abandon Confirm Dialog */}
                    <AlertDialog open={showAbandonConfirm} onOpenChange={setShowAbandonConfirm}>
                        <AlertDialogContent className="z-[160]">
                            <AlertDialogHeader>
                                <AlertDialogTitle>Abandon Session?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    This will end your current cooking session. History will be saved as "abandoned".
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                    className="bg-red-600 hover:bg-red-700 text-white"
                                    onClick={() => {
                                        onSessionEnd?.('abandon');
                                        setShowAbandonConfirm(false);
                                    }}
                                >
                                    Abandon
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>

                    {/* Complete Confirm Dialog */}
                    <AlertDialog open={showCompleteConfirm} onOpenChange={setShowCompleteConfirm}>
                        <AlertDialogContent className="z-[160]">
                            <AlertDialogHeader>
                                <AlertDialogTitle>Finish Cooking?</AlertDialogTitle>
                                <AlertDialogDescription>
                                    Great job! This will mark the session as complete and save it to your history.
                                </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                                <AlertDialogCancel>Not yet</AlertDialogCancel>
                                <AlertDialogAction
                                    className="bg-green-600 hover:bg-green-700 text-white"
                                    onClick={handleComplete}
                                >
                                    Finish!
                                </AlertDialogAction>
                            </AlertDialogFooter>
                        </AlertDialogContent>
                    </AlertDialog>

                    {/* Step Help Drawer (v15.2) */}
                    {session && (
                        <StepHelpDrawer
                            isOpen={helpTargetIndex !== null}
                            onClose={() => setHelpTargetIndex(null)}
                            sessionId={session.id}
                            stepIndex={helpTargetIndex ?? stepIdx}
                            onAddTimer={onTimerCreate ? (label, sec) => onTimerCreate(helpTargetIndex ?? stepIdx, label, sec) : undefined}
                        />
                    )}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
