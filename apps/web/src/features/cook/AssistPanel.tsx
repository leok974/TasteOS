/**
 * Assist Panel Component for Cook Mode
 */

import { useState } from 'react';
import { Sparkles, ChefHat, Flame, Droplet, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from '@/components/ui/sheet';
import { useCookAssist, type AssistResponse } from './hooks';

interface AssistPanelProps {
    recipeId: string;
    stepIndex: number;
}

export function AssistPanel({ recipeId, stepIndex }: AssistPanelProps) {
    const [open, setOpen] = useState(false);
    const [ingredient, setIngredient] = useState('');
    const [result, setResult] = useState<AssistResponse | null>(null);

    const assistMutation = useCookAssist();

    const handleSubstitute = () => {
        if (!ingredient.trim()) return;

        assistMutation.mutate(
            {
                recipe_id: recipeId,
                step_index: stepIndex,
                intent: 'substitute',
                payload: { ingredient: ingredient.trim() },
            },
            {
                onSuccess: (data) => setResult(data),
            }
        );
    };

    const handleMacros = () => {
        assistMutation.mutate(
            {
                recipe_id: recipeId,
                step_index: stepIndex,
                intent: 'macros',
                payload: {},
            },
            {
                onSuccess: (data) => setResult(data),
            }
        );
    };

    const handleFix = (problem: string) => {
        assistMutation.mutate(
            {
                recipe_id: recipeId,
                step_index: stepIndex,
                intent: 'fix',
                payload: { problem },
            },
            {
                onSuccess: (data) => setResult(data),
            }
        );
    };

    return (
        <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
                <Button
                    variant="outline"
                    className="h-11 rounded-2xl border-amber-100/60 hover:bg-amber-50/60"
                    data-testid="assist-open"
                >
                    <Sparkles className="h-4 w-4 mr-2" />
                    Cooking Assist
                </Button>
            </SheetTrigger>
            <SheetContent side="bottom" className="h-[85vh] rounded-t-3xl">
                <SheetHeader>
                    <SheetTitle className="font-serif text-2xl">Cooking Assistant</SheetTitle>
                    <SheetDescription>
                        Get help with substitutions, nutrition, and quick fixes
                    </SheetDescription>
                </SheetHeader>

                <div className="mt-6 space-y-6 overflow-y-auto h-[calc(85vh-120px)] pb-6">
                    {/* Substitute Section */}
                    <Card className="rounded-3xl border-amber-100/50">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <ChefHat className="h-5 w-5 text-amber-600" />
                                Substitute Ingredient
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <Input
                                placeholder="e.g., butter, milk, eggs..."
                                value={ingredient}
                                onChange={(e) => setIngredient(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleSubstitute()}
                                className="h-11 rounded-2xl"
                            />
                            <Button
                                onClick={handleSubstitute}
                                disabled={!ingredient.trim() || assistMutation.isPending}
                                className="w-full h-11 rounded-2xl bg-amber-600 hover:bg-amber-700"
                                data-testid="assist-substitute-run"
                            >
                                {assistMutation.isPending ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Finding substitute...
                                    </>
                                ) : (
                                    'Find Substitute'
                                )}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Macros Section */}
                    <Card className="rounded-3xl border-stone-100/50">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Flame className="h-5 w-5 text-orange-600" />
                                Nutrition Estimate
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <Button
                                onClick={handleMacros}
                                disabled={assistMutation.isPending}
                                variant="outline"
                                className="w-full h-11 rounded-2xl"
                                data-testid="assist-macros-run"
                            >
                                {assistMutation.isPending ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Analyzing...
                                    </>
                                ) : (
                                    'Estimate Macros'
                                )}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Quick Fixes */}
                    <Card className="rounded-3xl border-blue-100/50">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Droplet className="h-5 w-5 text-blue-600" />
                                Quick Fixes
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="grid grid-cols-2 gap-2">
                            <Button
                                onClick={() => handleFix('too_salty')}
                                disabled={assistMutation.isPending}
                                variant="outline"
                                className="h-11 rounded-2xl"
                                data-testid="assist-fix-too-salty"
                            >
                                Too Salty
                            </Button>
                            <Button
                                onClick={() => handleFix('too_spicy')}
                                disabled={assistMutation.isPending}
                                variant="outline"
                                className="h-11 rounded-2xl"
                                data-testid="assist-fix-too-spicy"
                            >
                                Too Spicy
                            </Button>
                            <Button
                                onClick={() => handleFix('too_thick')}
                                disabled={assistMutation.isPending}
                                variant="outline"
                                className="h-11 rounded-2xl"
                                data-testid="assist-fix-too-thick"
                            >
                                Too Thick
                            </Button>
                            <Button
                                onClick={() => handleFix('too_thin')}
                                disabled={assistMutation.isPending}
                                variant="outline"
                                className="h-11 rounded-2xl"
                                data-testid="assist-fix-too-thin"
                            >
                                Too Thin
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Result Display */}
                    {result && (
                        <Card className="rounded-3xl border-green-100/50 bg-green-50/30">
                            <CardHeader>
                                <div className="flex items-start justify-between">
                                    <CardTitle className="text-lg">{result.title}</CardTitle>
                                    <Badge variant="secondary" className="rounded-full">
                                        {result.source}
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2">
                                    {result.bullets.map((bullet, i) => (
                                        <li key={i} className="text-sm text-stone-700 flex gap-2">
                                            <span className="text-green-600">•</span>
                                            <span>{bullet}</span>
                                        </li>
                                    ))}
                                </ul>
                                {result.confidence !== undefined && (
                                    <div className="mt-3 text-xs text-stone-500">
                                        Confidence: {Math.round(result.confidence * 100)}%
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {assistMutation.isError && (
                        <Card className="rounded-3xl border-red-100/50 bg-red-50/30">
                            <CardContent className="pt-6">
                                <p className="text-sm text-red-700">
                                    Failed to get assistance. Please try again.
                                </p>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}
