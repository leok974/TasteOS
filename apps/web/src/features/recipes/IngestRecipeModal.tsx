
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useIngestRecipe } from './hooks';
import { ScrollText, Loader2, Sparkles } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useRouter } from 'next/navigation';

export function IngestRecipeModal() {
    const [isOpen, setIsOpen] = useState(false);
    const [text, setText] = useState('');
    const [hints, setHints] = useState({ servings: '', cuisine: '' });
    const [generateImage, setGenerateImage] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const ingestMutation = useIngestRecipe();
    const { toast } = useToast();
    const router = useRouter();

    // Auto-fill from hash fragment (magic link support)
    useEffect(() => {
        const hash = window.location.hash;
        if (hash && hash.startsWith('#tasteos-v1:')) {
            const token = hash.substring(1); // Remove # prefix
            setText(token);
            setIsOpen(true);
            // Clear hash from URL
            window.history.replaceState(null, '', window.location.pathname + window.location.search);
        }
    }, []);

    const handleIngest = async () => {
        setError(null);
        if (!text.trim()) return;

        try {
            await ingestMutation.mutateAsync({
                text,
                hints: {
                    servings: hints.servings ? parseInt(hints.servings) : undefined,
                    cuisine: hints.cuisine || undefined
                },
                generateImage
            }, {
                onSuccess: (recipe) => {
                    toast({
                        title: "Recipe Ingested",
                        description: `Created "${recipe.title}" from text.`,
                    });
                    setIsOpen(false);
                    setText('');
                    setHints({ servings: '', cuisine: '' });
                    // Verify with user if they want auto-redirect? Spec says "lands you on new recipe"
                    router.push(`/recipes/${recipe.id}`);
                },
                onError: (err) => {
                    setError(err instanceof Error ? err.message : "Ingestion failed");
                }
            });
        } catch (e) {
            setError(e instanceof Error ? e.message : "Action failed");
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                    <ScrollText className="h-4 w-4" />
                    Text Import
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Import from Text</DialogTitle>
                    <DialogDescription>
                        Paste a recipe from a website, chat, or document. We'll try to parse it automatically.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <Textarea
                            placeholder="Paste entire recipe here... (Title, Ingredients, Steps)"
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            className="h-[200px] font-mono text-sm"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="servings">Servings (Optional)</Label>
                            <Input
                                id="servings"
                                type="number"
                                placeholder="e.g. 4"
                                value={hints.servings}
                                onChange={(e) => setHints({ ...hints, servings: e.target.value })}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="cuisine">Cuisine Hint</Label>
                            <Input
                                id="cuisine"
                                placeholder="e.g. Italian"
                                value={hints.cuisine}
                                onChange={(e) => setHints({ ...hints, cuisine: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="gen-image"
                            checked={generateImage}
                            // Type cast or just rely on default input props, since our Checkbox forwards props to input
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGenerateImage(e.target.checked)}
                        />
                        <label
                            htmlFor="gen-image"
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                        >
                            <Sparkles className="h-3 w-3 text-amber-500" />
                            Generate Image (AI)
                        </label>
                    </div>

                    {error && (
                        <div className="text-sm text-destructive">{error}</div>
                    )}
                </div>

                <DialogFooter>
                    <Button onClick={handleIngest} disabled={!text.trim() || ingestMutation.isPending}>
                        {ingestMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Parse & Import
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
