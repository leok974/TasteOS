'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import {
    useCookSessionActive,
    useCookSessionStart,
    useCookSessionPatch,
    useCookSessionEnd,
    useCookSessionEvents,
} from '@/features/cook/hooks';
import { CookModeOverlay, CookStep } from '@/features/cook/components/CookModeOverlay';
import { useRecipe } from '@/features/recipes/hooks';
import type { RecipeStep } from '@/lib/api';
function apiStepToCookStep(step: RecipeStep): CookStep {
    return {
        title: step.title,
        minutes: step.minutes_est ?? 5,
        bullets: step.bullets ?? [],
    };
}

export function CookShell({ recipeId }: { recipeId: string }) {
    const router = useRouter();
    const queryClient = useQueryClient();
    const searchParams = useSearchParams();

    const { data: recipe, isLoading: recipeLoading } = useRecipe(recipeId);

    // Cook session hooks
    const { data: session, isLoading: sessionLoading } = useCookSessionActive(recipeId);
    const startSessionMutation = useCookSessionStart();
    const patchSessionMutation = useCookSessionPatch();
    const endSessionMutation = useCookSessionEnd();

    // Local State (mirrors page.tsx)
    const [stepIdx, setStepIdx] = useState(0);
    const [subOpen, setSubOpen] = useState(false); // CookModeOverlay handles passing onSubstitute?

    // Sync step index
    useEffect(() => {
        if (session && !patchSessionMutation.isPending) {
            setStepIdx(session.current_step_index);
        }
    }, [session, patchSessionMutation.isPending]);

    const handleStepChange = (newStepIdx: number) => {
        setStepIdx(newStepIdx);
        if (session) {
            patchSessionMutation.mutate({
                sessionId: session.id,
                patch: { current_step_index: newStepIdx }
            });
        }
    };

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

    // Subscribe
    useCookSessionEvents(session?.id);

    const toggleCheck = (key: string) => {
        const [stepIndex, bulletIndex] = key.split(':').map(Number);
        const checked = !checks[key];

        if (session) {
            patchSessionMutation.mutate({
                sessionId: session.id,
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
            patchSessionMutation.mutate({
                sessionId: session.id,
                patch: { servings_target: target }
            });
        }
    };

    const handleSessionEnd = (action: 'complete' | 'abandon') => {
        if (!session) return;
        endSessionMutation.mutate(
            { sessionId: session.id, action },
            {
                onSuccess: () => {
                    // Update cache
                    queryClient.invalidateQueries({ queryKey: ['cook-session', 'active', recipeId] });
                    // Navigate away explicitly
                    router.replace(`/recipes/${recipeId}`); // Remove ?cook=1
                },
                onError: (e) => {
                    if (action === 'abandon') {
                        router.replace(`/recipes/${recipeId}`);
                    }
                }
            }
        );
    };

    const handleClose = () => {
        // Just explicit close button -> navigate away
        // But wait, if session is active, closing overlay implies...?
        // In page.tsx, closing overlay kept session active but hid UI.
        // User wants URL gating. So closing UI = navigating away.
        router.replace(`/recipes/${recipeId}`);
    };

    // Auto-start if missing (Moved up to fix Rules of Hooks)
    useEffect(() => {
        if (!session && !sessionLoading && recipe && !startSessionMutation.isPending) {
            startSessionMutation.mutate(recipe.id);
        }
    }, [session, sessionLoading, recipe, startSessionMutation.isPending]);

    const cookSteps: CookStep[] = recipe?.steps.map(apiStepToCookStep) ?? [];

    if (recipeLoading || sessionLoading || !recipe) {
        return (
            <div className="fixed inset-0 z-[120] flex flex-col items-center justify-center bg-[#FAF9F6]">
                <Loader2 className="h-10 w-10 animate-spin text-amber-500" />
            </div>
        );
    }

    return (
        <CookModeOverlay
            open={true} // Always open when mounted in Shell
            onClose={handleClose}
            recipe={recipe}
            steps={cookSteps}
            stepIdx={stepIdx}
            setStepIdx={handleStepChange}
            checks={checks}
            onToggle={toggleCheck}
            onSubstitute={() => setSubOpen(true)} // Note: SubstituteModal needs to be rendered somewhere.
            session={session}
            onServingsChange={handleServingsChange}
            onTimerCreate={(label, durationSec) => {
                if (session) {
                    patchSessionMutation.mutate({
                        sessionId: session.id,
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
                        sessionId: session.id,
                        patch: {
                            timer_action: { timer_id: timerId, action },
                        }
                    });
                }
            }}
            onSessionEnd={handleSessionEnd}
        />
    );
}
