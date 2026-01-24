import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { useSubstitute } from './hooks';
import { Loader2, ArrowRight } from 'lucide-react';

interface SubstituteModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    recipeContext?: string;
}

export function SubstituteModal({ open, onOpenChange, recipeContext }: SubstituteModalProps) {
    const [ingredient, setIngredient] = useState('');
    const { mutate, isPending, data, reset } = useSubstitute();

    const handleSearch = () => {
        if (!ingredient) return;
        mutate({ ingredient, context: recipeContext });
    };

    const handleClose = () => {
        onOpenChange(false);
        setTimeout(() => {
            setIngredient('');
            reset();
        }, 300);
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Find a Substitute</DialogTitle>
                    <DialogDescription>
                        Enter an ingredient you're missing. We'll check your pantry and suggest a swap.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="flex gap-2">
                        <Input
                            placeholder="e.g. Buttermilk"
                            value={ingredient}
                            onChange={(e) => setIngredient(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        />
                        <Button onClick={handleSearch} disabled={!ingredient || isPending}>
                            {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                        </Button>
                    </div>

                    {data && (
                        <div className="rounded-xl bg-amber-50 p-4 border border-amber-100 animate-in fade-in slide-in-from-bottom-2">
                            <div className="flex items-center justify-between mb-2">
                                <span className="font-bold text-amber-900">{data.substitute}</span>
                                <span className="text-[10px] uppercase font-black tracking-widest text-amber-600/70 border border-amber-200 px-2 py-0.5 rounded-full">
                                    {data.confidence} Confidence
                                </span>
                            </div>
                            <p className="text-sm text-stone-700 leading-relaxed font-medium">
                                {data.instruction}
                            </p>
                        </div>
                    )}
                </div>

                <DialogFooter className="sm:justify-start">
                    <Button
                        type="button"
                        variant="outline"
                        onClick={handleClose}
                    >
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
