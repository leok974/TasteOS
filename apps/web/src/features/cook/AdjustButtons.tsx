'use client';

import { useState } from 'react';
import { 
    Flame, Droplets, Thermometer, AlertTriangle, X, Check,
    ArrowRight, Loader2
} from 'lucide-react';
import { 
    AdjustmentKind, AdjustPreviewResponse,
    previewAdjustment, applyAdjustment
} from '@/lib/api';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { useMutation } from '@tanstack/react-query';

interface Props {
    sessionId: string;
    stepIndex: number;
}

const KINDS: { kind: AdjustmentKind; label: string; icon: any }[] = [
    { kind: 'too_salty', label: 'Too Salty', icon: Droplets },
    { kind: 'too_spicy', label: 'Too Spicy', icon: Flame },
    { kind: 'too_thick', label: 'Too Thick', icon: Droplets },
    { kind: 'too_thin', label: 'Too Thin', icon: Droplets },
    { kind: 'burning', label: 'Burning', icon: AlertTriangle },
    { kind: 'no_browning', label: 'No Browning', icon: Thermometer },
    { kind: 'undercooked', label: 'Undercooked', icon: Thermometer },
];

export function AdjustButtons({ sessionId, stepIndex }: Props) {
    const [preview, setPreview] = useState<AdjustPreviewResponse | null>(null);
    const [activeKind, setActiveKind] = useState<AdjustmentKind | null>(null);

    const previewMutation = useMutation({
        mutationFn: (kind: AdjustmentKind) => previewAdjustment(sessionId, {
            step_index: stepIndex,
            kind: kind
        }),
        onSuccess: (data) => setPreview(data),
    });

    const applyMutation = useMutation({
        mutationFn: () => {
            if (!preview) throw new Error("No preview");
            return applyAdjustment(sessionId, {
                adjustment_id: preview.adjustment.id,
                step_index: stepIndex,
                steps_override: preview.steps_preview,
                adjustment: preview.adjustment
            });
        },
        onSuccess: () => {
            setPreview(null);
            setActiveKind(null);
        }
    });

    const handleKindClick = (kind: AdjustmentKind) => {
        if (activeKind === kind) {
            setActiveKind(null);
            setPreview(null);
            return;
        }
        setActiveKind(kind);
        setPreview(null);
        previewMutation.mutate(kind);
    };

    return (
        <div className="mt-4 border-t border-dashed border-stone-200 pt-3">
             <div className="flex flex-wrap gap-2">
                {KINDS.map(k => {
                    const Icon = k.icon;
                    const isActive = activeKind === k.kind;
                    return (
                        <button
                            key={k.kind}
                            data-testid={`adjust-${k.kind.replace('_', '-')}`}
                            onClick={() => handleKindClick(k.kind)}
                            disabled={previewMutation.isPending && !isActive && activeKind !== null}
                            className={cn(
                                "flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide border transition-all",
                                isActive 
                                    ? "bg-amber-100 border-amber-300 text-amber-900 shadow-sm transform scale-105" 
                                    : "bg-white border-stone-100 text-stone-500 hover:border-amber-200 hover:text-stone-700"
                            )}
                        >
                            <Icon className="h-3 w-3" />
                            {k.label}
                        </button>
                    );
                })}
            </div>

            {/* Preview Panel */}
            {(activeKind && (preview || previewMutation.isPending)) && (
                <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50/50 p-3 animate-in fade-in slide-in-from-top-2">
                    {previewMutation.isPending ? (
                        <div className="flex items-center justify-center p-4">
                            <Loader2 className="h-5 w-5 animate-spin text-amber-500" />
                        </div>
                    ) : preview ? (
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="text-sm font-bold text-stone-900">{preview.adjustment.title}</h4>
                                <div className="text-[10px] text-amber-700 font-mono">
                                    {(preview.adjustment.confidence * 100).toFixed(0)}% match
                                </div>
                            </div>
                            
                            <ul className="space-y-1 mb-4">
                                {preview.adjustment.bullets.map((b, i) => (
                                    <li key={i} className="flex gap-2 text-xs text-stone-700 leading-snug">
                                        <span className="text-amber-500">•</span>
                                        {b}
                                    </li>
                                ))}
                            </ul>

                             {preview.adjustment.warnings.length > 0 && (
                                <div className="mb-3 rounded-lg bg-orange-100 text-orange-900 text-xs p-2">
                                    {preview.adjustment.warnings.map((w, i) => (
                                        <div key={i} className="flex gap-1.5">
                                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                                            <span>{w}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="flex items-center gap-2">
                                <Button
                                    size="sm"
                                    onClick={() => {
                                        setPreview(null);
                                        setActiveKind(null);
                                    }}
                                    data-testid="adjust-preview-cancel"
                                    variant="outline"
                                    className="h-8 text-xs rounded-lg border-stone-200"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    size="sm"
                                    onClick={() => applyMutation.mutate()}
                                    disabled={applyMutation.isPending}
                                    data-testid="adjust-preview-apply"
                                    className="h-8 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white flex-1"
                                >
                                    {applyMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : "Apply Fix"}
                                </Button>
                            </div>
                        </div>
                    ) : null}
                </div>
            )}
        </div>
    );
}
