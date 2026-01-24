
import { useState } from 'react';
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
import { useImportRecipe } from './hooks';
import { Upload, FileJson, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { PortableRecipe } from '@/lib/api';

export function ImportRecipeModal() {
    const [isOpen, setIsOpen] = useState(false);
    const [jsonInput, setJsonInput] = useState('');
    const [regenImage, setRegenImage] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const importMutation = useImportRecipe();
    const { toast } = useToast();

    const handleImport = async () => {
        setError(null);
        try {
            const payload = JSON.parse(jsonInput) as PortableRecipe;
            // Simple schema validation
            if (!payload.schema_version || !payload.recipe) {
                throw new Error("Invalid recipe JSON format");
            }

            await importMutation.mutateAsync({
                payload,
                mode: 'dedupe', // Default
                regenImage,
            }, {
                onSuccess: (data) => {
                    toast({
                        title: data.created ? "Recipe Imported" : "Recipe Exists",
                        description: data.message,
                        variant: data.created ? "default" : "secondary"
                    });
                    setIsOpen(false);
                    setJsonInput('');
                },
                onError: (err) => {
                    setError(err instanceof Error ? err.message : "Import failed");
                }
            });
        } catch (e) {
            setError(e instanceof Error ? e.message : "Invalid JSON");
        }
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (ev) => {
            const text = ev.target?.result as string;
            setJsonInput(text);
            setError(null);
        };
        reader.readAsText(file);
    };

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" className="gap-2">
                    <Upload className="h-4 w-4" />
                    Import
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Import Recipe</DialogTitle>
                    <DialogDescription>
                        Paste a recipe JSON or upload a file.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <Textarea
                            placeholder='{"schema_version": "tasteos.recipe.v1", ...}'
                            value={jsonInput}
                            onChange={(e) => setJsonInput(e.target.value)}
                            className="h-[150px] font-mono text-xs"
                        />
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <Button variant="secondary" size="sm" className="gap-2">
                                <FileJson className="h-4 w-4" />
                                Upload JSON
                            </Button>
                            <input
                                type="file"
                                accept=".json"
                                className="absolute inset-0 opacity-0 cursor-pointer"
                                onChange={handleFileUpload}
                            />
                        </div>

                        <div className="flex items-center space-x-2">
                            <Checkbox
                                id="regen"
                                checked={regenImage}
                                onCheckedChange={(c) => setRegenImage(!!c)}
                            />
                            <label
                                htmlFor="regen"
                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                            >
                                Regenerate Image
                            </label>
                        </div>
                    </div>

                    {error && (
                        <div className="text-sm text-destructive">{error}</div>
                    )}
                </div>

                <DialogFooter>
                    <Button onClick={handleImport} disabled={!jsonInput || importMutation.isPending}>
                        {importMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Import Recipe
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
