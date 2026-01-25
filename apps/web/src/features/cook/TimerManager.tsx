/**
 * Timer Manager Component for Cook Mode
 */

import { useState, useEffect, useRef } from 'react';
import { Clock, Play, Pause, Check, Trash2, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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
import { cn } from '@/lib/cn';
import type { CookTimer } from './hooks';

interface TimerManagerProps {
    stepIndex: number;
    timers: Record<string, CookTimer>;
    onTimerCreate: (label: string, durationSec: number) => void;
    onTimerAction: (timerId: string, action: 'start' | 'pause' | 'done' | 'delete') => void;
}

function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function requestNotificationPermission() {
    if (typeof window !== 'undefined' && "Notification" in window && Notification.permission === "default") {
        Notification.requestPermission().then(permission => {
            console.log("Notification permission result:", permission);
        });
    }
}

function playTimerSound() {
    try {
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContext) return;
        
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.5);
        
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
        
        osc.start();
        osc.stop(ctx.currentTime + 0.5);
    } catch (e) {
        console.error("Failed to play timer sound:", e);
    }
}

function TimerCard({
    timerId,
    timer,
    onAction,
}: {
    timerId: string;
    timer: CookTimer;
    onAction: (action: 'start' | 'pause' | 'done' | 'delete') => void;
}) {
    const [remaining, setRemaining] = useState(timer.duration_sec);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showDoneAlert, setShowDoneAlert] = useState(false);

    const actionRef = useRef(onAction);

    useEffect(() => {
        actionRef.current = onAction;
    }, [onAction]);

    useEffect(() => {
        const calculateRemaining = () => {
            if (timer.state === 'running') {
                if (timer.due_at) {
                    // v9 Logic: Absolute Due Date
                    const now = Date.now();
                    const dueMs = new Date(timer.due_at).getTime();
                    return Math.max(0, Math.ceil((dueMs - now) / 1000));
                } else if (timer.started_at) {
                    // v8 Logic: Elapsed Time
                    const now = Date.now();
                    const startedMs = new Date(timer.started_at).getTime();
                    const currentElapsed = Math.floor((now - startedMs) / 1000);
                    const totalElapsed = (timer.elapsed_sec || 0) + currentElapsed;
                    return Math.max(0, timer.duration_sec - totalElapsed);
                }
            } else if (timer.state === 'paused') {
                 if (timer.remaining_sec != null) {
                     return timer.remaining_sec;
                 } else {
                     const totalElapsed = timer.elapsed_sec || 0;
                     return Math.max(0, timer.duration_sec - totalElapsed);
                 }
            } else if (timer.state === 'done') {
                return 0;
            }
            return timer.duration_sec;
        };

        const update = () => {
            const val = calculateRemaining();
            setRemaining(val);
            if (val === 0 && timer.state === 'running') {
                console.log("Timer finished:", timer.label);
                playTimerSound();
                
                if (typeof Notification !== 'undefined') {
                    if (Notification.permission === "granted") {
                        new Notification("Timer Done!", { 
                            body: `${timer.label} is ready!`,
                            icon: '/placeholders/recipe-amber-1.svg',
                        });
                    } else if (Notification.permission === "default") {
                        // Try requesting one last time (unlikely to work without user gesture but worth a shot)
                        Notification.requestPermission().then(p => {
                            if (p === "granted") {
                                new Notification("Timer Done!", { body: `${timer.label} is ready!` });
                            }
                        });
                    } else {
                        console.warn("Notifications blocked or not granted.");
                    }
                }
                setShowDoneAlert(true);
                actionRef.current('done');
            }
        };

        update();

        if (timer.state === 'running') {
            const interval = setInterval(update, 200);
            return () => clearInterval(interval);
        }
    }, [timer.state, timer.due_at, timer.remaining_sec, timer.started_at, timer.duration_sec, timer.elapsed_sec]);

    const stateColors = {
        created: 'bg-stone-100 text-stone-600',
        running: 'bg-amber-100 text-amber-900',
        paused: 'bg-blue-100 text-blue-900',
        done: 'bg-green-100 text-green-900',
    };

    return (
        <div
            className={cn(
                'flex items-center gap-3 rounded-2xl border p-3',
                timer.state === 'running' ? 'border-amber-200 bg-amber-50/50' : 'border-stone-200 bg-white'
            )}
        >
            <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-stone-800 truncate">{timer.label}</div>
                <div className="mt-0.5 flex items-center gap-2">
                    <span className="font-mono text-lg font-bold text-stone-900">{formatTime(remaining)}</span>
                    <Badge className={cn('rounded-full text-[9px] font-black uppercase', stateColors[timer.state])}>
                        {timer.state}
                    </Badge>
                </div>
            </div>

            <div className="flex gap-1">
                {timer.state === 'created' || timer.state === 'paused' ? (
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 rounded-xl p-0"
                        onClick={() => {
                            requestNotificationPermission();
                            onAction('start');
                        }}
                        data-testid={`timer-start-${timerId}`}
                    >
                        <Play className="h-4 w-4" />
                    </Button>
                ) : null}

                {timer.state === 'running' ? (
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 rounded-xl p-0"
                        onClick={() => onAction('pause')}
                        data-testid={`timer-pause-${timerId}`}
                    >
                        <Pause className="h-4 w-4" />
                    </Button>
                ) : null}

                {timer.state !== 'done' ? (
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 rounded-xl p-0 text-green-600 hover:text-green-700"
                        onClick={() => onAction('done')}
                        data-testid={`timer-done-${timerId}`}
                    >
                        <Check className="h-4 w-4" />
                    </Button>
                ) : null}

                <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 rounded-xl p-0 text-red-600 hover:text-red-700"
                    onClick={() => setShowDeleteConfirm(true)}
                    data-testid={`timer-delete-${timerId}`}
                >
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>

            <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
                <AlertDialogContent className="z-[130]">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Timer?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This will delete "{timer.label}". This action cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => {
                            onAction('delete');
                            setShowDeleteConfirm(false);
                        }}>
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <AlertDialog open={showDoneAlert} onOpenChange={setShowDoneAlert}>
                <AlertDialogContent className="z-[130]">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Timer Finished!</AlertDialogTitle>
                        <AlertDialogDescription>
                            {timer.label} is done.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogAction onClick={() => setShowDoneAlert(false)}>
                            Okay
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}

export function TimerManager({ stepIndex, timers, onTimerCreate, onTimerAction }: TimerManagerProps) {
    const [showPresets, setShowPresets] = useState(false);

    // Filter timers for this step
    const stepTimers = Object.entries(timers).filter(
        ([_, timer]) => timer.step_index === stepIndex
    );

    const presets = [
        { label: '1 minute', seconds: 60 },
        { label: '5 minutes', seconds: 300 },
        { label: '10 minutes', seconds: 600 },
        { label: '15 minutes', seconds: 900 },
    ];

    return (
        <div className="space-y-3">
            {stepTimers.length > 0 ? (
                <div className="space-y-2">
                    <div className="text-[10px] font-black uppercase tracking-widest text-stone-500">
                        Active Timers
                    </div>
                    {stepTimers.map(([id, timer]) => (
                        <TimerCard
                            key={id}
                            timerId={id}
                            timer={timer}
                            onAction={(action) => onTimerAction(id, action)}
                        />
                    ))}
                </div>
            ) : null}

            {!showPresets ? (
                <Button
                    variant="outline"
                    className="w-full h-11 rounded-2xl border-amber-100/60 hover:bg-amber-50/60"
                    onClick={() => setShowPresets(true)}
                    data-testid={`timer-add-${stepIndex}`}
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Timer
                </Button>
            ) : (
                <div className="space-y-2">
                    <div className="text-[10px] font-black uppercase tracking-widest text-stone-500">
                        Quick Timers
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        {presets.map((preset) => (
                            <Button
                                key={preset.seconds}
                                variant="outline"
                                className="h-11 rounded-2xl border-amber-100/60 hover:bg-amber-50/60 font-semibold"
                                onClick={() => {
                                    requestNotificationPermission();
                                    onTimerCreate(preset.label, preset.seconds);
                                    setShowPresets(false);
                                }}
                                data-testid={`timer-preset-${preset.seconds}`}
                            >
                                <Clock className="h-4 w-4 mr-2" />
                                {preset.label}
                            </Button>
                        ))}
                    </div>
                    <Button
                        variant="ghost"
                        className="w-full h-9 rounded-xl text-sm"
                        onClick={() => setShowPresets(false)}
                    >
                        Cancel
                    </Button>
                </div>
            )}
        </div>
    );
}
