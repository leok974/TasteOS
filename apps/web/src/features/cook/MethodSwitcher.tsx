
import { useState } from 'react';
import { ChefHat, Flame, Clock, Sparkles, RefreshCw, Undo2, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/cn';
import { useCookMethods, useCookMethodPreview, useCookMethodApply, useCookMethodReset } from './hooks'; // Ensure these are exported from hooks.ts

interface MethodSwitcherProps {
    sessionId: string;
    activeMethodKey?: string | null;
}

export function MethodSwitcher({ sessionId, activeMethodKey }: MethodSwitcherProps) {
    const [open, setOpen] = useState(false);
    const [selectedMethod, setSelectedMethod] = useState<string | null>(null);

    const { data: methodsData } = useCookMethods();
    const { mutate: previewMethod, data: previewData, isPending: isPreviewLoading, reset: resetPreview } = useCookMethodPreview();
    const { mutate: applyMethod, isPending: isApplyLoading } = useCookMethodApply();
    const { mutate: resetMethod, isPending: isResetLoading } = useCookMethodReset();

    const handleMethodSelect = (key: string) => {
        if (key === selectedMethod) return;
        setSelectedMethod(key);
        resetPreview();
        if (key) {
            previewMethod({ sessionId, methodKey: key });
        }
    };

    const handleApply = () => {
        if (!selectedMethod || !previewData) return;
        applyMethod({
            sessionId,
            methodKey: selectedMethod,
            steps: previewData.steps_preview,
            tradeoffs: previewData.tradeoffs
        }, {
            onSuccess: () => {
                setOpen(false);
                setSelectedMethod(null);
                resetPreview();
            }
        });
    };

    const handleReset = () => {
        resetMethod({ sessionId }, {
            onSuccess: () => {
                setOpen(false);
                setSelectedMethod(null);
                resetPreview();
            }
        });
    };

    // Find label for active method
    const activeMethodLabel = methodsData?.methods.find(m => m.key === activeMethodKey)?.label || "Original";

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" size="sm" className={cn("h-8 gap-1.5 rounded-full border-dashed", activeMethodKey ? "border-amber-500 bg-amber-50 text-amber-700 hover:bg-amber-100" : "text-stone-500")}>
                    <ChefHat className="h-3.5 w-3.5" />
                    <span className="text-xs font-medium">{activeMethodKey ? activeMethodLabel : 'Switch Method'}</span>
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Method Switcher</DialogTitle>
                    <DialogDescription>
                        Adapt this recipe to your equipment without changing the core flavors.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 md:grid-cols-[1fr_1.2fr]">
                    {/* Left: Method List */}
                    <div className="space-y-2">
                        <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">Select Equipment</div>

                        <button
                            onClick={() => handleMethodSelect('original')} // 'original' logic handled differently? Or just use as deselect
                            className={cn(
                                "w-full text-left px-3 py-3 rounded-xl border text-sm transition-all",
                                !selectedMethod && !activeMethodKey ? "border-stone-800 bg-stone-50 ring-1 ring-stone-800" : "border-stone-200 hover:border-stone-300"
                            )}
                            disabled // Can't select "Original" like this yet, use Reset button
                        >
                            <div className="font-semibold text-stone-900">Original Recipe</div>
                            <div className="text-xs text-stone-500 mt-0.5">Standard preparation</div>
                        </button>

                        {methodsData?.methods.map((method) => (
                            <button
                                key={method.key}
                                onClick={() => handleMethodSelect(method.key)}
                                className={cn(
                                    "w-full text-left px-3 py-3 rounded-xl border text-sm transition-all group",
                                    selectedMethod === method.key
                                        ? "border-amber-500 bg-amber-50 ring-1 ring-amber-500"
                                        : "border-stone-200 hover:border-amber-200 hover:bg-amber-50/50"
                                )}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="font-semibold text-stone-900 group-hover:text-amber-900">{method.label}</div>
                                    {activeMethodKey === method.key && <Badge variant="secondary" className="text-[10px] h-5">Active</Badge>}
                                </div>
                                <div className="text-xs text-stone-500 mt-1 flex items-center gap-1.5 line-clamp-2">
                                    {method.summary}
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* Right: Preview / Tradeoffs */}
                    <div className="border-l pl-6 -ml-6 md:ml-0 md:pl-0 md:border-l-0">
                        <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">Preview Changes</div>

                        {selectedMethod ? (
                            isPreviewLoading ? (
                                <div className="h-40 flex items-center justify-center text-stone-400 text-sm animate-pulse">
                                    <Sparkles className="h-4 w-4 mr-2" /> Generating variant...
                                </div>
                            ) : previewData ? (
                                <div className="space-y-4">
                                    {/* Tradeoffs Card */}
                                    <Card className="p-3 bg-stone-50/50 border-stone-100">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div>
                                                <div className="text-[10px] text-stone-500 font-medium uppercase">Time</div>
                                                <div className={cn("text-sm font-bold flex items-center gap-1", previewData.tradeoffs.time_delta_min < 0 ? "text-green-600" : "text-stone-700")}>
                                                    <Clock className="h-3.5 w-3.5" />
                                                    {previewData.tradeoffs.time_delta_min === 0 ? "Same" :
                                                        previewData.tradeoffs.time_delta_min > 0 ? `+${previewData.tradeoffs.time_delta_min}m` : `${previewData.tradeoffs.time_delta_min}m`}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-stone-500 font-medium uppercase">Effort / Cleanup</div>
                                                <div className="text-sm font-bold text-stone-700 capitalize flex items-center gap-1">
                                                    <Sparkles className="h-3.5 w-3.5" />
                                                    {previewData.tradeoffs.effort} / {previewData.tradeoffs.cleanup}
                                                </div>
                                            </div>
                                        </div>
                                        {previewData.tradeoffs.texture_notes.length > 0 && (
                                            <div className="mt-2 pt-2 border-t border-stone-100">
                                                <div className="text-[10px] text-stone-500 font-medium uppercase mb-1">Texture Notes</div>
                                                <div className="flex flex-wrap gap-1">
                                                    {previewData.tradeoffs.texture_notes.map((note: string, i: number) => (
                                                        <Badge key={i} variant="outline" className="text-[10px] bg-white border-stone-200 text-stone-600 font-normal">
                                                            {note}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </Card>

                                    {/* Steps Diff Preview */}
                                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
                                        {/* MVP: Just list new steps titles with simple diff styling */}
                                        {previewData.steps_preview.map((step: any, i: number) => (
                                            <div key={i} className="text-sm border-l-2 border-amber-200 pl-3 py-1">
                                                <div className="font-semibold text-stone-800">
                                                    <span className="text-stone-400 font-mono text-xs mr-2">{i + 1}.</span>
                                                    {step.title}
                                                </div>
                                                <div className="text-xs text-stone-500 mt-0.5 line-clamp-2">
                                                    {step.bullets?.[0]}
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="pt-2 flex flex-col gap-2">
                                        <Button
                                            onClick={handleApply}
                                            disabled={isApplyLoading}
                                            className="w-full bg-amber-500 hover:bg-amber-600 text-white rounded-xl"
                                        >
                                            {isApplyLoading ? "Applying..." : "Apply Changes"}
                                        </Button>
                                        <div className="text-[10px] text-center text-stone-400">
                                            This creates a temporary session override.
                                        </div>
                                    </div>
                                </div>
                            ) : null
                        ) : activeMethodKey ? (
                            <div className="flex flex-col items-center justify-center py-10 text-center">
                                <div className="text-sm font-medium text-stone-900 mb-1">Active Method: {activeMethodLabel}</div>
                                <div className="text-xs text-stone-500 mb-4 px-8">
                                    You are currently using the {activeMethodLabel} variant instructions.
                                </div>
                                <Button
                                    variant="outline"
                                    onClick={handleReset}
                                    disabled={isResetLoading}
                                    className="text-red-600 border-red-100 hover:bg-red-50"
                                >
                                    <Undo2 className="h-3.5 w-3.5 mr-2" />
                                    Reset to Original
                                </Button>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-40 text-stone-400 text-sm">
                                <ArrowRight className="h-6 w-6 mb-2 opacity-20" />
                                Select a method to preview changes
                            </div>
                        )}
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
