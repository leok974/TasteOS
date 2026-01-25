"use client";

import { useCookSessionWhy } from "../hooks";
import { Loader2, TrendingUp, Activity } from "lucide-react";

export function WhyPanel({ sessionId }: { sessionId: string }) {
    const { data, isLoading, error } = useCookSessionWhy(sessionId, true);

    if (isLoading) return <div className="p-4"><Loader2 className="animate-spin h-4 w-4" /></div>;
    
    if (error) {
        return (
            <div className="p-4 text-sm text-red-500">
                Error loading data: {(error as Error).message}
            </div>
        );
    }

    if (!data) return <div className="p-4 text-sm text-muted-foreground">No data available (Response empty).</div>;

    const signals = data.signals || [];

    if (!signals.length) {
        return (
            <div className="p-4 text-sm text-muted-foreground italic">
                No recent activity signals found.
            </div>
        );
    }

    return (
        <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
                 <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    Suggestion Analysis
                 </div>
                 <div className="text-xs bg-muted px-2 py-0.5 rounded-full font-mono">
                    {Math.round(data.confidence * 100)}% Conf
                 </div>
            </div>
            
            {data.reason && (
                 <div className="text-sm font-medium text-primary border border-primary/20 bg-primary/5 rounded p-2">
                     <div className="text-xs text-muted-foreground mb-0.5 uppercase tracking-wide">Primary Reason</div>
                     <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> {data.reason}
                     </div>
                 </div>
            )}
            
            <div className="space-y-2">
                 <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Signals ({signals.length})</div>
                 <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {signals.map((sig: any, i) => (
                        <div key={i} className="text-xs border-l-2 border-border pl-3 py-1">
                            <div className="flex justify-between items-baseline">
                                <span className={`font-medium ${sig.step_index === data.suggested_step_index ? 'text-primary' : 'text-foreground'}`}>
                                    {formatSignalType(sig.type)}
                                </span>
                                <span className="text-muted-foreground font-mono">{sig.age_sec}s ago</span>
                            </div>
                            <div className="text-[10px] text-muted-foreground mt-0.5 grid grid-cols-[auto_1fr] gap-2">
                                <span className="font-mono bg-muted/50 px-1 rounded">Step {sig.step_index + 1}</span>
                                <span className="truncate">{formatMeta(sig.meta)}</span>
                            </div>
                        </div>
                    ))}
                 </div>
            </div>
        </div>
    );
}

function formatSignalType(type: string) {
    const map: Record<string, string> = {
        "timer_start": "Started Timer",
        "timer_done": "Timer Finished",
        "check_step": "Item Checked",
        "step_navigate": "Manual Navigation",
    };
    return map[type] || type.replace(/_/g, " ");
}

function formatMeta(meta: any) {
    if (!meta) return "";
    // Remove complex objects
    const simple = { ...meta };
    delete simple.step; 
    delete simple.bullet;
    if (Object.keys(simple).length === 0) return "";
    return JSON.stringify(simple).replace(/["{}]/g, "").replace(/:/g, ": ");
}
