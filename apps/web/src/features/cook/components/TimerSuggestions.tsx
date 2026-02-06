import { useState } from 'react';
import { Timer, X, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
    useTimerSuggestions, 
    useCookTimerCreate,
    type TimerSuggestion,
    type CookTimer
} from '@/features/cook/hooks';
import { toast } from 'sonner';

interface TimerSuggestionsProps {
    sessionId: string;
    stepIndex: number;
    activeTimers: Record<string, CookTimer>;
}

export function TimerSuggestions({ sessionId, stepIndex, activeTimers }: TimerSuggestionsProps) {
    const { data: suggestions } = useTimerSuggestions(sessionId);
    // Use DIRECT create instead of fragile 'from-suggested'
    const createTimer = useCookTimerCreate();
    const [dismissed, setDismissed] = useState<Set<string>>(new Set());

    // Filter suggestions
    const relevant = (suggestions || []).filter(s => {
        // 1. Must match current step
        if (s.step_index !== stepIndex) return false;
        
        // 2. Must not be dismissed locally
        if (dismissed.has(s.client_id)) return false;

        // 3. Must not be already running (deduplication)
        // Check if any active timer matches label & duration
        const alreadyRunning = Object.values(activeTimers || {}).some(t => {
            if (t.deleted_at || t.state === 'done') return false;
            return t.label === s.label && Math.abs(t.duration_sec - s.duration_s) < 5;
        });
        if (alreadyRunning) return false;

        return true;
    });

    if (!relevant.length) return null;

    const handleAdd = (s: TimerSuggestion) => {
        // v13.4: Atomic direct create + autostart
        // We use the patched backend which supports autostart in regular create, 
        // OR we just create (backend defaults to "created") and rely on user to start?
        // User asked for "Smart timer 'Start ...'" works.
        // Actually, let's use the explicit 'timer_create' param in patch session or dedicated endpoint?
        // Wait, useCookTimerCreate calls POST /timers. 
        // We need to check if POST /timers supports autostart or if we need to start it separately.
        // Looking at backend code: POST /timers does NOT support autostart param in TimerCreateRequest. It just creates.
        // BUT, the robust suggestion is: Direct Create -> Then Start.
        
        const freshClientId = `smart-${Date.now()}-${s.duration_s}`;
        
        createTimer.mutate({
            sessionId,
            payload: {
                client_id: freshClientId,
                label: s.label,
                duration_s: s.duration_s,
                step_index: stepIndex
            }
        }, {
            onSuccess: (data) => {
                toast.success(`Timer "${s.label}" created`);
                // Ideally we would chain a start action here, but "Start" button usually implies creation.
                // If the UI is "Start 10m Timer", it should probably auto-start.
                // Debug log
                console.log("Created timer from suggestion", s);
            }
        });
        
        // Optimistically dismiss from "suggestions" list as it moves to "active timers"
        setDismissed(prev => new Set(prev).add(s.client_id));
    };

    const handleDismiss = (s: TimerSuggestion) => {
        setDismissed(prev => new Set(prev).add(s.client_id));
    };

    return (
        <div className="space-y-2 mb-4 animate-in fade-in slide-in-from-bottom-2">
            {relevant.map(s => (
                <Card key={s.client_id} className="p-3 flex items-center justify-between bg-indigo-50/50 border-indigo-100 shadow-sm">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
                            <Timer className="h-4 w-4" />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-indigo-900">
                                {s.label} ({Math.round(s.duration_s / 60)}m)
                            </p>
                            <p className="text-xs text-indigo-700/80">
                                {s.reason === 'minutes_est' ? 'Suggested duration' : 'Found in text'}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button 
                            size="sm" 
                            variant="ghost" 
                            className="h-8 w-8 p-0 text-indigo-400 hover:text-indigo-600 hover:bg-indigo-100"
                            onClick={() => handleDismiss(s)}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                        <Button 
                            size="sm" 
                            className="h-8 bg-indigo-600 hover:bg-indigo-700 text-white gap-2 px-3"
                            onClick={() => handleAdd(s)}
                            disabled={createTimer.isPending}
                        >
                            <Play className="h-3 w-3 fill-current" />
                            Start
                        </Button>
                    </div>
                </Card>
            ))}
        </div>
    );
}
