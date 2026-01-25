"use client";

import { useCookSessionLog } from "../hooks";
import { formatDistanceToNow } from "date-fns";
import { Loader2 } from "lucide-react";

export function WhyPanel({ sessionId }: { sessionId: string }) {
    const { data: events, isLoading, error } = useCookSessionLog(sessionId);

    if (isLoading) return <div className="flex justify-center p-4"><Loader2 className="h-4 w-4 animate-spin" /></div>;
    
    if (error) return <div className="text-sm text-red-500 p-4">Failed to load history: {error.message}</div>;

    if (!events?.length) {
        return (
            <div className="flex flex-col items-center justify-center p-8 text-center">
                <div className="text-sm text-muted-foreground">No history recorded yet.</div>
            </div>
        );
    }

    return (
        <div className="h-[300px] overflow-y-auto pr-2">
            <div className="space-y-4 p-1">
                {events.map((evt: any) => (
                    <div key={evt.id} className="flex gap-3 text-sm border-l-2 border-border pl-4 py-1">
                        <div className="flex-1">
                            <div className="font-semibold text-foreground">{formatEventType(evt.type)}</div>
                            {evt.meta && Object.keys(evt.meta).length > 0 && (
                                <div className="text-xs text-muted-foreground mt-1 bg-muted/50 p-1.5 rounded font-mono">
                                    {formatMeta(evt.type, evt.meta)}
                                </div>
                            )}
                        </div>
                        <div className="text-xs text-muted-foreground whitespace-nowrap pt-1">
                            {formatDistanceToNow(new Date(evt.created_at), { addSuffix: true })}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function formatEventType(type: string) {
    const map: Record<string, string> = {
        "session_start": "Started Cooking",
        "step_navigate": "Navigated Step",
        "check_step": "Checked Item",
        "uncheck_step": "Unchecked Item",
        "timer_create": "Created Timer",
        "timer_start": "Started Timer",
        "timer_pause": "Paused Timer",
        "timer_done": "Timer Finished",
        "timer_delete": "Deleted Timer",
        "session_complete": "Finished Cooking",
        "servings_change": "Changed Servings"
    };
    return map[type] || type.replace(/_/g, " ");
}

function formatMeta(type: string, meta: any) {
    // Custom formatting for specific event types
    if (type === "step_navigate") {
        return `Step ${meta.from + 1} -> ${meta.to + 1}`; // 1-based index for display
    }
    if (type === "check_step" || type === "uncheck_step") {
        return `Step ${meta.step + 1}, Item ${meta.bullet + 1}`;
    }
    if (type === "timer_create") {
         return `${meta.label || 'Timer'} (${Math.floor(meta.duration / 60)}m)`;
    }
    
    // Default json dump for debug
    return JSON.stringify(meta);
}
