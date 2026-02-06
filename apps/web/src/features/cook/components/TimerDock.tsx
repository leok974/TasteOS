
import React, { useState, useEffect } from 'react';
import { useCookTimerAction } from '../hooks';
import type { CookSession, CookTimer } from '../hooks';
import { Play, Pause, X, Check } from 'lucide-react';
import { cn } from '../../../lib/cn';

interface TimerDockProps {
    session: CookSession;
    sessionId: string;
    className?: string;
}

export function TimerDock({ session, sessionId, className }: TimerDockProps) {
    const activeTimers = Object.entries(session.timers || {}).filter(([_, t]) => !t.deleted_at);

    if (activeTimers.length === 0) return null;

    return (
        <div className={cn("fixed left-0 right-0 p-4 bg-white border-t shadow-lg z-[140] flex gap-4 overflow-x-auto safe-area-bottom", className || "bottom-0")}>
            {activeTimers.map(([id, timer]) => (
                <TimerCard key={id} id={id} timer={timer} sessionId={sessionId} />
            ))}
        </div>
    );
}

function TimerCard({ id, timer, sessionId }: { id: string, timer: CookTimer, sessionId: string }) {
    const { mutate: action } = useCookTimerAction();
    const [remaining, setRemaining] = useState(0);

    // Calculate remaining time
    useEffect(() => {
        const tick = () => {
            // Logic mirrors backend "remaining" calculation or local valid
            // If state == created: duration
            // If state == running: duration - (now - started_at)
            // If state == paused: paused_remaining (store in snapshot or calc)
            // If state == done: 0

            if (timer.state === 'created') {
                setRemaining(timer.duration_sec);
            } else if (timer.state === 'done') {
                setRemaining(0);
            } else if (timer.state === 'paused') {
                // Legacy v9 support: remaining_sec is explicitly set
                if (typeof timer.remaining_sec === 'number') {
                    setRemaining(timer.remaining_sec);
                }
                // v13 support: calculated from timestamps
                else if (timer.started_at && timer.paused_at) {
                    const start = new Date(timer.started_at).getTime();
                    const pause = new Date(timer.paused_at).getTime();
                    // In v13, start time is shifted on resume so (pause - start) is always valid active duration
                    const elapsed = (pause - start) / 1000;
                    setRemaining(Math.max(0, Math.round(timer.duration_sec - elapsed)));
                } else {
                    setRemaining(timer.duration_sec); // Fallback
                }
            } else if (timer.state === 'running') {
                // v9 or v13 running: due_at (v9) or started_at (v13)
                if (timer.due_at) {
                     const now = Date.now();
                     const due = new Date(timer.due_at).getTime();
                     setRemaining(Math.max(0, Math.ceil((due - now) / 1000)));
                } else if (timer.started_at) {
                    const start = new Date(timer.started_at).getTime();
                    const now = Date.now();
                    const elapsed = (now - start) / 1000;
                    setRemaining(Math.max(0, Math.round(timer.duration_sec - elapsed)));
                }
            }
        };

        tick(); // Initial
        const interval = setInterval(tick, 1000);
        return () => clearInterval(interval);
    }, [timer]);

    const formatTime = (sec: number) => {
        const m = Math.floor(sec / 60);
        const s = Math.floor(sec % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const isRunning = timer.state === 'running';
    const isPaused = timer.state === 'paused';
    const isDone = timer.state === 'done';

    return (
        <div className={cn(
            "flex items-center gap-3 px-4 py-2 rounded-lg border min-w-[200px] shadow-sm",
            isDone ? "bg-green-50 border-green-200" : "bg-white border-gray-200"
        )}>
            <div className="flex-1">
                <div className="text-xs text-gray-500 font-medium truncate max-w-[120px]" title={timer.label}>{timer.label}</div>
                <div className={cn("text-xl font-bold font-mono", isDone ? "text-green-600" : "text-gray-900")}>
                    {isDone ? "DONE" : formatTime(remaining)}
                </div>
            </div>

            <div className="flex gap-1">
                {!isDone && (
                    <>
                        {isRunning ? (
                            <button onClick={() => action({ sessionId, timerId: id, payload: { action: 'pause' } })} className="p-2 hover:bg-gray-100 rounded-full">
                                <Pause size={16} />
                            </button>
                        ) : (
                            <button onClick={() => action({ sessionId, timerId: id, payload: { action: isPaused ? 'resume' : 'start' } })} className="p-2 hover:bg-gray-100 rounded-full">
                                <Play size={16} />
                            </button>
                        )}
                    </>
                )}

                {isDone ? (
                    <button onClick={() => action({ sessionId, timerId: id, payload: { action: 'delete' } })} className="p-2 hover:bg-green-100 rounded-full text-green-600">
                        <X size={16} />
                    </button>
                ) : (
                    <button onClick={() => action({ sessionId, timerId: id, payload: { action: 'delete' } })} className="p-2 hover:bg-red-50 rounded-full text-red-500">
                        <X size={16} />
                    </button>
                )}
            </div>
        </div>
    );
}
