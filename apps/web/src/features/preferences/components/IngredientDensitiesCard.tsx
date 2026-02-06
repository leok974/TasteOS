import React, { useState } from 'react';
import { useDensityList, useDensityUpsert, useDensityDelete } from '../useDensities';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FileWarning, Save, Trash2, Plus, FlaskConical } from 'lucide-react';

export function IngredientDensitiesCard() {
    const [search, setSearch] = useState('');
    const { data: densities, isLoading } = useDensityList(search);
    const upsertMutation = useDensityUpsert();
    const deleteMutation = useDensityDelete();

    // Form State
    const [isAdding, setIsAdding] = useState(false);
    const [newName, setNewName] = useState('');
    const [massVal, setMassVal] = useState('120');
    const [massUnit, setMassUnit] = useState('g');
    const [volVal, setVolVal] = useState('1');
    const [volUnit, setVolUnit] = useState('cup');
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    const handleSave = async () => {
        setErrorMsg(null);
        if (!newName.trim()) {
            setErrorMsg("Ingredient name is required");
            return;
        }

        try {
            await upsertMutation.mutateAsync({
                ingredient_name: newName,
                density: {
                    mass_value: parseFloat(massVal),
                    mass_unit: massUnit,
                    vol_value: parseFloat(volVal),
                    vol_unit: volUnit
                }
            });
            setIsAdding(false);
            setNewName('');
            // Reset to defaults
            setMassVal('120');
            setMassUnit('g');
            setVolVal('1');
            setVolUnit('cup');
        } catch (e: any) {
            setErrorMsg(e.message || "Failed to save. Check values.");
            console.error(e);
        }
    };

    const handleDelete = (id: string) => {
        if (confirm("Remove this density override?")) {
            deleteMutation.mutate(id);
        }
    };

    return (
        <Card>
            <CardHeader>
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <FlaskConical className="h-5 w-5" />
                            Ingredient Densities
                        </CardTitle>
                        <CardDescription>
                            Define custom densities for accurate mass ↔ volume conversions.
                        </CardDescription>
                    </div>
                    {!isAdding && (
                        <Button variant="outline" size="sm" onClick={() => setIsAdding(true)}>
                            <Plus className="h-4 w-4 mr-2" />
                            Add Override
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Add Form */}
                {isAdding && (
                    <div className="rounded-lg border p-4 bg-muted/30 space-y-4">
                        <div className="grid gap-2">
                            <Label>Ingredient Name</Label>
                            <Input 
                                value={newName} 
                                onChange={e => setNewName(e.target.value)} 
                                placeholder="e.g. Almond Flour"
                            />
                        </div>
                        
                        <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
                            <div className="flex items-center gap-2 flex-1">
                                <Input 
                                    type="number" 
                                    value={massVal} 
                                    onChange={e => setMassVal(e.target.value)} 
                                    className="w-20"
                                />
                                <select 
                                    value={massUnit}
                                    onChange={e => setMassUnit(e.target.value)}
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    <option value="g">grams (g)</option>
                                    <option value="oz">ounces (oz)</option>
                                    <option value="lb">pounds (lb)</option>
                                    <option value="kg">kilograms (kg)</option>
                                </select>
                            </div>
                            
                            <span className="font-bold text-muted-foreground">=</span>
                            
                            <div className="flex items-center gap-2 flex-1">
                                <Input 
                                    type="number" 
                                    value={volVal} 
                                    onChange={e => setVolVal(e.target.value)} 
                                    className="w-20"
                                />
                                <select 
                                    value={volUnit}
                                    onChange={e => setVolUnit(e.target.value)}
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    <option value="cup">cup</option>
                                    <option value="ml">ml</option>
                                    <option value="tbsp">tbsp</option>
                                    <option value="tsp">tsp</option>
                                    <option value="l">liter</option>
                                    <option value="fl oz">fl oz</option>
                                </select>
                            </div>
                        </div>

                        {errorMsg && (
                            <div className="text-sm text-red-500 font-medium flex items-center gap-2">
                                <FileWarning className="h-4 w-4" />
                                {errorMsg}
                            </div>
                        )}

                        <div className="flex justify-end gap-2 pt-2">
                            <Button variant="ghost" size="sm" onClick={() => setIsAdding(false)}>Cancel</Button>
                            <Button size="sm" onClick={handleSave} disabled={upsertMutation.isPending}>
                                {upsertMutation.isPending ? "Saving..." : "Save Override"}
                            </Button>
                        </div>
                    </div>
                )}

                {/* Search & List */}
                <div className="space-y-4">
                    <Input 
                        placeholder="Search overrides..." 
                        value={search} 
                        onChange={e => setSearch(e.target.value)}
                    />
                    
                    <div className="rounded-md border divide-y">
                        {isLoading ? (
                            <div className="p-4 text-center text-muted-foreground">Loading...</div>
                        ) : densities?.length === 0 ? (
                            <div className="p-8 text-center text-muted-foreground">
                                No density overrides found.
                            </div>
                        ) : (
                            densities?.map(d => (
                                <div key={d.id} className="p-3 flex items-center justify-between hover:bg-muted/10">
                                    <div className="grid gap-1">
                                        <div className="font-medium">{d.display_name}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {d.density_g_per_ml.toFixed(3)} g/ml
                                            {d.source === 'user' && <span className="ml-2 px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold">USER</span>}
                                        </div>
                                    </div>
                                    <Button 
                                        variant="ghost" 
                                        size="sm" 
                                        className="h-8 w-8 px-0 text-muted-foreground hover:text-red-500"
                                        onClick={() => handleDelete(d.id)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
