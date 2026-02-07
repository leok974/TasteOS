import React from 'react';
import { useCookAutoflow, useCookSessionPatch, useCookTimerCreate, useCookTimerAction, useCookSessionEnd, CookSession, AutoflowSuggestion } from '../hooks';
import { CheckCircle2, ChevronRight, Play, Timer, ArrowRight, Check, HelpCircle } from 'lucide-react';
import { cn } from '../../../lib/cn';

interface NextUpPanelProps {
    session: CookSession;
    recipe: any;
    className?: string;
}

export function NextUpPanel({ session, recipe, className }: NextUpPanelProps) {
    // Extract state for Autoflow
    const checkedKeys = React.useMemo(() => {
        const keys: string[] = [];
        if (session.step_checks) {
            Object.entries(session.step_checks).forEach(([stepIdx, bullets]) => {
                Object.entries(bullets).forEach(([bulletIdx, checked]) => {
                    if (checked) keys.push(`${stepIdx}-${bulletIdx}`);
                });
            });
        }
        return keys;
    }, [session.step_checks]);

    const activeTimerIds = React.useMemo(() => {
        return Object.entries(session.timers || {})
            .filter(([_, t]) => t.state === 'running' || t.state === 'paused')
            .map(([id, _]) => id);
    }, [session.timers]);

    // Use Autoflow v15.2.2
    const { data: autoflow, isLoading } = useCookAutoflow(
        session.id,
        session.current_step_index,
        session.state_version || 0,
        checkedKeys,
        activeTimerIds
    );

    const { mutate: patchSession } = useCookSessionPatch();
    const { mutate: createTimer } = useCookTimerCreate();
    const { mutate: timerAction } = useCookTimerAction();
    const { mutate: endSession } = useCookSessionEnd();

    if (isLoading || !autoflow || !autoflow.suggestions.length) return null;

    const topSuggestion = autoflow.suggestions[0];
    const secondarySuggestions = autoflow.suggestions.slice(1);

    const handleSuggestion = (suggestion: AutoflowSuggestion) => {
        const { op, payload } = suggestion.action;

        switch (op) {
            case 'create_timer':
                const clientId = `autoflow-${Date.now()}`;
                // Adapt payload key names
                createTimer({
                    sessionId: session.id,
                    payload: {
                        client_id: clientId,
                        label: suggestion.label,
                        duration_sec: payload.duration_s || payload.duration_sec || 60,
                        step_index: session.current_step_index,
                        ...payload
                    }
                });
                break;
                
            case 'navigate_step':
                if (typeof payload.step_index === 'number') {
                    patchSession({
                        sessionId: session.id,
                        patch: { current_step_index: payload.step_index }
                    });
                }
                break;

            case 'patch_session':
                // Check if we are completing a step
                if (payload.mark_step_complete) {
                    patchSession({
                        sessionId: session.id,
                        patch: { mark_step_complete: payload.mark_step_complete }
                    });
                }
                // Check if we are ending session
                else if (payload.status === 'completed') {
                    endSession({ sessionId: session.id, action: 'complete' });
                }
                else {
                    // Generic patch fallthrough
                    patchSession({
                        sessionId: session.id,
                        patch: payload
                    });
                }
                break;

            case 'open_help':
                console.log("Open Help requested", payload);
                break;
                
            case 'none':
            default:
                break;
        }
    };
    
    const getIcon = (type: AutoflowSuggestion['type']) => {
        switch(type) {
            case 'next_step': return <ArrowRight className="w-4 h-4" />;
            case 'start_timer': return <Play className="w-4 h-4" />;
            case 'check_item': return <Check className="w-4 h-4" />;
            case 'complete_step': return <CheckCircle2 className="w-4 h-4" />;
            case 'open_help': return <HelpCircle className="w-4 h-4" />;
            case 'prep_next': return <ChevronRight className="w-4 h-4" />;
            default: return <Play className="w-4 h-4" />;
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
                        ✨ Next Up {autoflow.source === 'ai' && <span className="text-[10px] text-amber-500 bg-amber-100 px-1 rounded">AI</span>}
                     </div>
                </div>
                
                <div className="flex flex-wrap gap-2 items-center">
                    {/* Primary Action */}
                    <button
                        onClick={() => handleSuggestion(topSuggestion)}
                        className={cn(
                            "rounded-full px-4 py-2 text-sm font-bold flex items-center gap-2 transition-all active:scale-95 shadow-sm",
                            "bg-amber-500 hover:bg-amber-600 text-white"
                        )}
                        data-testid={`autoflow-action-${topSuggestion.type}`}
                    >
                        {getIcon(topSuggestion.type)}
                        <span>{topSuggestion.label}</span>
                    </button>

                    {/* Secondary Actions */}
                    {secondarySuggestions.map((suggestion, i) => (
                        <button
                            key={i}
                            onClick={() => handleSuggestion(suggestion)}
                            className="rounded-full px-3 py-1.5 text-xs font-semibold flex items-center gap-2 transition-all active:scale-95 bg-white hover:bg-gray-50 text-gray-600 border border-gray-200"
                        >
                            {getIcon(suggestion.type)}
                            <span>{suggestion.label}</span>
                        </button>
                    ))}
                    
                    {topSuggestion.why && (
                        <span className="text-xs text-amber-800/60 italic ml-1 max-w-[200px] truncate">
                            {topSuggestion.why}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
