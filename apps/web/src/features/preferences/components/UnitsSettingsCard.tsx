import React from 'react';
import { useUnitPrefs, useUpdateUnitPrefs, UnitPrefsUpdate } from '../hooks';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Loader2 } from 'lucide-react';

export function UnitsSettingsCard() {
    const { data: prefs, isLoading, error } = useUnitPrefs();
    const updatePrefs = useUpdateUnitPrefs();

    const handleUpdate = (updates: UnitPrefsUpdate) => {
        updatePrefs.mutate(updates);
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center p-6">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card className="border-red-200 bg-red-50">
                <CardContent className="p-6 text-red-600">
                    Failed to load unit preferences.
                </CardContent>
            </Card>
        );
    }

    if (!prefs) return null;

    return (
        <Card>
            <CardHeader>
                <CardTitle>Workspace Units</CardTitle>
                <CardDescription>
                    Configure how units are displayed and calculated across your workspace.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                
                {/* System Selection */}
                <div className="grid gap-2">
                    <Label htmlFor="system">Measurement System</Label>
                    <select
                        id="system"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                        value={prefs.system}
                        onChange={(e) => handleUpdate({ system: e.target.value as "us" | "metric" })}
                        disabled={updatePrefs.isPending}
                    >
                        <option value="us">US Customary (oz, cups, lbs)</option>
                        <option value="metric">Metric (g, ml, kg)</option>
                    </select>
                </div>

                {/* Rounding Mode */}
                <div className="grid gap-2">
                    <Label htmlFor="rounding">Rounding Logic</Label>
                    <select
                        id="rounding"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                        value={prefs.rounding}
                        onChange={(e) => handleUpdate({ rounding: e.target.value as "cook" | "decimal" })}
                        disabled={updatePrefs.isPending}
                    >
                        <option value="cook">Cook-Friendly (fractions, nice numbers)</option>
                        <option value="decimal">Strict Decimal</option>
                    </select>
                    <p className="text-[0.8rem] text-muted-foreground">
                        "Cook" rounds to nearest 1/4 cup or whole numbers when appropriate.
                    </p>
                </div>

                {/* Decimal Places (Only if decimal mode) */}
                {prefs.rounding === 'decimal' && (
                    <div className="grid gap-2">
                        <Label htmlFor="decimals">Decimal Places</Label>
                        <Input
                            id="decimals"
                            type="number"
                            min={0}
                            max={5}
                            value={prefs.decimal_places}
                            onChange={(e) => handleUpdate({ decimal_places: parseInt(e.target.value) || 2 })}
                            disabled={updatePrefs.isPending}
                        />
                    </div>
                )}

                {/* Density Policy */}
                <div className="grid gap-2">
                    <Label htmlFor="density">Volume/Weight Conversion Policy</Label>
                    <select
                        id="density"
                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                        value={prefs.density_policy}
                        onChange={(e) => handleUpdate({ density_policy: e.target.value as "known_only" | "common_only" })}
                        disabled={updatePrefs.isPending}
                    >
                        <option value="known_only">Strict (Only known ingredients)</option>
                        <option value="common_only">Relaxed (Use water density as fallback)</option>
                    </select>
                    <p className="text-[0.8rem] text-muted-foreground">
                        Dictates how we handle converting cups to grams when the ingredient density is unknown.
                    </p>
                </div>

                {/* Cross-Type Conversion Switch */}
                <div className="flex items-center justify-between space-x-2 rounded-lg border p-3 shadow-sm">
                    <div className="space-y-0.5">
                        <Label htmlFor="cross-type">Allow Cross-Type Conversions</Label>
                        <p className="text-[0.8rem] text-muted-foreground">
                            Automatically convert weight to volume (and vice-versa) if density is available.
                        </p>
                    </div>
                    <Switch
                        id="cross-type"
                        checked={prefs.allow_cross_type}
                        onCheckedChange={(checked) => handleUpdate({ allow_cross_type: checked })}
                        disabled={updatePrefs.isPending}
                    />
                </div>

            </CardContent>
        </Card>
    );
}
