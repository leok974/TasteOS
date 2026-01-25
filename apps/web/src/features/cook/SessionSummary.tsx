import { useState } from 'react';
import { Check, ChevronRight, FileText, Save, Utensils } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { useCookSessionSummary, useCookNotesPreview, useCookNotesApply } from './hooks';
import { cn } from '@/lib/cn';
import { useToast } from '@/hooks/use-toast';

interface SessionSummaryProps {
    sessionId: string;
    recipeId: string;
    onClose?: () => void;
}

export function SessionSummary({ sessionId, recipeId, onClose }: SessionSummaryProps) {
    const { toast } = useToast();
    const { data, isLoading } = useCookSessionSummary(sessionId, true);
    
    // Notes Selection State
    const [includeMethod, setIncludeMethod] = useState(true);
    const [includeServings, setIncludeServings] = useState(true);
    const [includeAdjustments, setIncludeAdjustments] = useState(true);
    const [freeformNote, setFreeformNote] = useState('');
    
    // Preview/Save State
    const [preview, setPreview] = useState<any>(null);
    const previewMutation = useCookNotesPreview();
    const applyMutation = useCookNotesApply();
    
    // View State: summary | preview | saved
    const [viewMode, setViewMode] = useState<'summary' | 'preview' | 'saved'>('summary');

    if (isLoading || !data) {
        return <div className="p-8 text-center text-stone-500">Loading summary...</div>;
    }

    const { session, highlights, stats, notes_suggestions } = data;

    const handlePreview = () => {
        previewMutation.mutate({
            sessionId,
            include: {
                method: includeMethod,
                servings: includeServings,
                adjustments: includeAdjustments,
                freeform: freeformNote
            }
        }, {
            onSuccess: (resp) => {
                setPreview(resp.proposal);
                setViewMode('preview');
            }
        });
    };

    const handleApply = () => {
        if (!preview) return;
        applyMutation.mutate({
            sessionId,
            recipeId,
            notes: preview.recipe_patch.notes_append
        }, {
            onSuccess: () => {
                setViewMode('saved');
                toast({ title: "Notes Saved", description: "Added to recipe notes successfully." });
            }
        });
    };

    if (viewMode === 'saved') {
        return (
             <div className="flex flex-col items-center justify-center p-12 space-y-4 text-center animate-in fade-in">
                 <div className="h-16 w-16 bg-green-100 rounded-full flex items-center justify-center text-green-600 mb-2">
                     <Check className="h-8 w-8" />
                 </div>
                 <h2 className="text-xl font-bold text-amber-900">Session Complete!</h2>
                 <p className="text-stone-600 max-w-xs">
                     Your notes have been saved to the recipe.
                 </p>
                 <Button onClick={onClose} className="mt-4 w-full max-w-xs">
                     Back to Recipe
                 </Button>
             </div>
        );
    }

    if (viewMode === 'preview') {
         return (
             <div className="space-y-6 p-1 animate-in slide-in-from-right-4">
                 <div className="flex items-center gap-2 mb-4">
                     <Button variant="ghost" size="sm" onClick={() => setViewMode('summary')}>Back</Button>
                     <h2 className="text-lg font-bold text-amber-900">Review Notes</h2>
                 </div>
                 
                 <Card className="bg-stone-50 border-stone-200">
                     <CardContent className="p-4 font-mono text-sm text-stone-700 whitespace-pre-wrap">
                         {preview.preview_markdown}
                     </CardContent>
                 </Card>
                 
                 <div className="flex gap-3">
                     <Button 
                        variant="outline" 
                        className="flex-1" 
                        onClick={() => setViewMode('summary')}
                    >
                        Edit Selection
                    </Button>
                     <Button 
                        className="flex-1 bg-amber-600 hover:bg-amber-700 text-white"
                        onClick={handleApply}
                        disabled={applyMutation.isPending}
                        data-testid="save-notes-apply"
                    >
                        {applyMutation.isPending ? "Saving..." : "Confirm & Save"}
                    </Button>
                 </div>
             </div>
         );
    }

    return (
        <div className="space-y-6 pb-20 animate-in fade-in" data-testid="summary-open">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-black text-amber-900 font-serif">Session Summary</h2>
                    <p className="text-sm text-stone-500">{new Date(session.completed_at || Date.now()).toLocaleDateString()}</p>
                </div>
            </div>

            {/* Highlights */}
            {highlights.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {highlights.map((h: string, i: number) => (
                        <Badge key={i} variant="secondary" className="bg-amber-100 text-amber-900 border-amber-200">
                            {h}
                        </Badge>
                    ))}
                </div>
            )}

            {/* Stats */}
            <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-3 bg-stone-50 rounded-xl border border-stone-100">
                    <div className="text-xs text-stone-500 uppercase tracking-widest font-bold">Duration</div>
                    <div className="text-xl font-black text-stone-800">{stats.duration_minutes}m</div>
                </div>
                <div className="p-3 bg-stone-50 rounded-xl border border-stone-100">
                    <div className="text-xs text-stone-500 uppercase tracking-widest font-bold">Timers</div>
                    <div className="text-xl font-black text-stone-800">{stats.timers_total}</div>
                </div>
                <div className="p-3 bg-stone-50 rounded-xl border border-stone-100">
                    <div className="text-xs text-stone-500 uppercase tracking-widest font-bold">Adjustments</div>
                    <div className="text-xl font-black text-stone-800">{stats.adjustments_total}</div>
                </div>
            </div>

            <Separator />

            {/* Notes Section */}
            <div className="space-y-4">
                 <div className="flex items-center gap-2">
                     <FileText className="h-5 w-5 text-amber-600" />
                     <h3 className="font-bold text-lg text-stone-800">Save to Recipe Notes?</h3>
                 </div>
                 
                 <div className="space-y-3">
                     <div className="flex items-start gap-3 p-3 rounded-lg border border-transparent hover:bg-stone-50 transition-colors">
                         <Checkbox 
                            id="inc-method" 
                            checked={includeMethod} 
                            onChange={(e) => setIncludeMethod(e.target.checked)} 
                         />
                         <div className="grid gap-1.5 leading-none">
                             <label htmlFor="inc-method" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                 Include Method
                             </label>
                             <p className="text-xs text-stone-500">Record that you used the {data.session?.method_key || 'Default'} method.</p>
                         </div>
                     </div>

                     <div className="flex items-start gap-3 p-3 rounded-lg border border-transparent hover:bg-stone-50 transition-colors">
                         <Checkbox 
                            id="inc-servings" 
                            checked={includeServings} 
                            onChange={(e) => setIncludeServings(e.target.checked)} 
                         />
                         <div className="grid gap-1.5 leading-none">
                             <label htmlFor="inc-servings" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                 Include Servings
                             </label>
                             <p className="text-xs text-stone-500">Record scaling to {data.session?.servings_target || 1} servings.</p>
                         </div>
                     </div>
                     
                     {notes_suggestions.map((s: any) => (
                         <div key={s.id} className="flex items-start gap-3 p-3 rounded-lg border border-transparent hover:bg-stone-50 transition-colors">
                              <Checkbox 
                                id={`s-${s.id}`} 
                                checked={includeAdjustments} 
                                onChange={(e) => setIncludeAdjustments(e.target.checked)} 
                              />
                               <div className="grid gap-1.5 leading-none">
                                 <label htmlFor={`s-${s.id}`} className="text-sm font-medium leading-none">
                                     {s.text}
                                 </label>
                                 <p className="text-xs text-stone-500">Auto-suggested from adjustment log</p>
                             </div>
                         </div>
                     ))}
                     
                     <div className="pt-2">
                         <label className="text-xs font-bold uppercase text-stone-500 mb-1.5 block">Custom Note</label>
                         <Textarea 
                            placeholder="What would you change next time?" 
                            className="bg-white"
                            value={freeformNote}
                            onChange={(e) => setFreeformNote(e.target.value)}
                         />
                     </div>
                 </div>
            </div>

            <Button 
                onClick={handlePreview} 
                className="w-full h-12 rounded-2xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-lg shadow-lg shadow-amber-900/10"
                disabled={previewMutation.isPending}
                data-testid="save-notes-preview"
            >
                {previewMutation.isPending ? "Generating Preview..." : "Preview & Save"}
            </Button>
            
            <div className="text-center">
                <button onClick={onClose} className="text-xs text-stone-400 hover:text-stone-600 underline">
                    Skip & Close
                </button>
            </div>
        </div>
    );
}
