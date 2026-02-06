import React from 'react';
import { useCookNext, useCookSessionPatch, useCookTimerCreate, useCookTimerAction, useCookSessionEnd } from '../hooks';
import { CookSession } from '../hooks';
import type { CookNextAction } from '../../../lib/api';
import { CheckCircle2, ChevronRight, Play, Timer, ArrowRight, Check } from 'lucide-react';
import { cn } from '../../../lib/cn';

interface NextUpPanelProps {
    session: CookSession;
    recipe: any;
    className?: string;
}

export function NextUpPanel({ session, recipe, className }: NextUpPanelProps) {
    const { data: nextUp, isLoading } = useCookNext(session.id);
    const { mutate: patchSession } = useCookSessionPatch();
    const { mutate: createTimer } = useCookTimerCreate();
    const { mutate: timerAction } = useCookTimerAction();
    const { mutate: endSession } = useCookSessionEnd();

    if (isLoading || !nextUp || !nextUp.actions.length) return null;

    const handleAction = (action: CookNextAction) => {
        if (action.type === 'go_to_step') {
            if (typeof action.step_idx === 'number') {
                 patchSession({
                     sessionId: session.id,
                     patch: { current_step_index: action.step_idx }
                 });
            }
        } 
        else if (action.type === 'start_timer') {
            if (action.timer_id) {
                timerAction({ 
                    sessionId: session.id, 
                    timerId: action.timer_id, 
                    payload: { action: 'start' } 
                });
            }
        }
        else if (action.type === 'create_timer') {
             const clientId = `next-up-${Date.now()}`;
             createTimer({
                 sessionId: session.id,
                 payload: {
                     client_id: clientId,
                     label: action.label,
                     duration_s: action.duration_s || 60,
                     step_index: action.step_idx || session.current_step_index
                 }
             });
        }
        else if (action.type === 'mark_step_done') {
            if (typeof action.step_idx === 'number') {
                const step = recipe.steps.find((s: any) => s.step_index === action.step_idx);
                if (step && step.bullets) {
                    step.bullets.forEach((_: any, idx: number) => {
                        // Check if already checked? 
                        // The heuristics say if incomplete, so at least one is unchecked.
                        // We set all to checked.
                        const isChecked = session.step_checks[String(action.step_idx)]?.[String(idx)];
                        if (!isChecked) {
                            patchSession({
                                sessionId: session.id,
                                patch: {
                                    step_checks_patch: {
                                        step_index: action.step_idx!,
                                        bullet_index: idx,
                                        checked: true
                                    }
                                }
                            });
                        }
                    });
                }
            }
        }
        else if (action.type === 'complete_session') {
            endSession({ sessionId: session.id, action: 'complete' });
        }
    };
    
    // Icon mapping
    const getIcon = (type: string) => {
        switch(type) {
            case 'go_to_step': return <ArrowRight className="w-4 h-4" />;
            case 'start_timer': return <Play className="w-4 h-4" />;
            case 'create_timer': return <Timer className="w-4 h-4" />;
            case 'mark_step_done': return <Check className="w-4 h-4" />;
            case 'complete_session': return <CheckCircle2 className="w-4 h-4" />;
            default: return null;
        }
    };

    return (
        <div 
            className={cn("bg-amber-50/80 border-b border-amber-100 p-3 shadow-sm backdrop-blur-sm", className)}
            data-testid="next-up-panel"
        >
            <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                     <div className="text-xs font-bold text-amber-700 uppercase tracking-wider flex items-center gap-1">
                        ✨ Next Up
                        {nextUp.reason && <span className="font-normal normal-case text-amber-600/70 ml-1">• {nextUp.reason}</span>}
                     </div>
                </div>
                
                <div className="flex flex-wrap gap-2">
                    {nextUp.actions.slice(0, 3).map((action, i) => (
                        <button
                            key={i}
                            onClick={() => handleAction(action)}
                            className={cn(
                                "rounded-full px-3 py-1.5 text-sm font-semibold flex items-center gap-2 transition-all active:scale-95 shadow-sm",
                                i === 0 
                                    ? "bg-amber-500 hover:bg-amber-600 text-white" 
                                    : "bg-white hover:bg-gray-50 text-gray-700 border border-gray-200"
                            )}
                            data-testid={`next-action-${action.type}`}
                        >
                            {getIcon(action.type)}
                            <span>{action.label}</span>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
