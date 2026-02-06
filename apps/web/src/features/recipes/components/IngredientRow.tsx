import { useState, useEffect, useMemo } from 'react';
import { useUnitConversion } from "@/features/recipes/useUnitConversion";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/cn";
import { useDensityUpsert } from "@/features/preferences/useDensities";
import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useUnitPrefs } from '@/features/preferences/hooks';

export function formatQtyLocal(qty: number, options?: { rounding?: 'cook' | 'decimal', decimals?: number }) {
    if (!qty && qty !== 0) return '';
    
    // Decimal mode
    if (options?.rounding === 'decimal') {
        return qty.toFixed(options.decimals || 2);
    }

    // Cook mode (fractions)
    const decimal = qty % 1;
    const whole = Math.floor(qty);
    let fraction = '';

    if (Math.abs(decimal - 0.5) < 0.01) fraction = '½';
    else if (Math.abs(decimal - 0.25) < 0.01) fraction = '¼';
    else if (Math.abs(decimal - 0.75) < 0.01) fraction = '¾';
    else if (Math.abs(decimal - 0.33) < 0.02) fraction = '⅓';
    else if (Math.abs(decimal - 0.66) < 0.02) fraction = '⅔';
    else if (Math.abs(decimal - 0.125) < 0.01) fraction = '⅛';

    if (whole === 0 && fraction) return fraction;
    if (whole > 0 && fraction) return `${whole} ${fraction}`;
    
    // Fallback for non-fractional numbers in cook mode
    if (Math.abs(Math.round(qty) - qty) < 0.05) return Math.round(qty).toString();
    
    return Number(qty.toFixed(2)).toString();
}

const METRIC_UNITS = ['g', 'kg', 'ml', 'l'];
const US_UNITS = ['oz', 'lb', 'cup', 'tbsp', 'tsp'];

export function IngredientRow({ 
    ingredient, 
    scaleFactor, 
    mode 
}: { 
    ingredient: { name: string; qty: number | null; unit: string | null };
    scaleFactor: number;
    mode: 'default' | 'metric' | 'imperial';
}) {
    const { mutate } = useUnitConversion();
    const { mutate: upsertDensity, isPending: isSavingDensity } = useDensityUpsert();
    const { data: prefs } = useUnitPrefs();

    const originalQty = ingredient.qty ? ingredient.qty * scaleFactor : null;
    const originalUnit = ingredient.unit;

    const [currentQty, setCurrentQty] = useState(originalQty);
    const [currentUnit, setCurrentUnit] = useState(originalUnit);
    const [isConverting, setIsConverting] = useState(false);
    
    // Density Prompts
    const [densityNeeded, setDensityNeeded] = useState(false);
    const [densityValue, setDensityValue] = useState(''); // user input grams
    const [lastAttempt, setLastAttempt] = useState<any>(null); // store last conversion attempt

    // Handle Mode Changes
    useEffect(() => {
        if (originalQty === null || !originalUnit || mode === 'default') {
            setCurrentQty(originalQty);
            setCurrentUnit(originalUnit);
            setDensityNeeded(false);
            return;
        }

        // Use Server-Side Smart Selection
        const targetSystem = mode === 'metric' ? 'metric' : 'us_customary';
        attemptConversion(originalQty, originalUnit, null, targetSystem);

    }, [mode, originalQty, originalUnit, ingredient.name]);

    const attemptConversion = (qty: number, from: string, to: string | null = null, system: any = null) => {
        setIsConverting(true);
        setDensityNeeded(false);
        
        mutate({
            qty: qty,
            from_unit: from,
            to_unit: to || undefined,
            target_system: system,
            ingredient_name: ingredient.name,
            force_cross_type: true
        }, {
            onSuccess: (data) => {
                setCurrentQty(data.qty);
                setCurrentUnit(data.unit);
                setIsConverting(false);
                
                // If approx/low confidence, maybe show warning?
                // But specifically for density needed flow:
                if (data.is_approx && data.confidence !== 'high') {
                     // Could hint at density set here
                     // For v14.2 we handle explicit prompts primarily
                }
            },
            onError: (err) => {
                // If error is 400 density required, show UI
                // Or if we decide client-side to prompt for approx
                console.error(err);
                setIsConverting(false);
                setCurrentQty(originalQty);
                setCurrentUnit(originalUnit);
                
                // Simplified heuristic: if cross-type failed or returned low confidence
                // But hooking into mutate error is hard to inspect status code directly without custom fetcher wrapper in useUnitConversion
                // Let's assume for now we just show it if user manually triggers and fails?
            }
        });
        
        setLastAttempt({ qty, from, to, system });
    };

    const sortedUnits = useMemo(() => {
        if (!prefs) return [...METRIC_UNITS, ...US_UNITS];
        const primary = prefs.system === 'metric' ? METRIC_UNITS : US_UNITS;
        const secondary = prefs.system === 'metric' ? US_UNITS : METRIC_UNITS;
        return [...primary, ...secondary];
    }, [prefs]);

    // Manual Override (Click to pick unit)
    const handleUnitSelect = (target: string) => {
            if (originalQty === null || !originalUnit) return;
            attemptConversion(originalQty, originalUnit, target);
            
            // Heuristic: If Mass <-> Vol, prompt density if not high confidence?
            // Actually, let's just show a tiny "Approximation" indicator that allows fixing
    };
    
    const handleSaveDensity = () => {
        const val = parseFloat(densityValue);
        if (!val || val <= 0) return;
        
        upsertDensity({
            ingredient_name: ingredient.name,
            density: {
                value: val,
                per_unit: "cup" // We'll ask "grams per cup"
            }
        }, {
            onSuccess: () => {
                setDensityNeeded(false);
                // Retry conversion
                if (lastAttempt) {
                    attemptConversion(lastAttempt.qty, lastAttempt.from, lastAttempt.to, lastAttempt.system);
                }
            }
        });
    };

    return (
        <div className="group flex flex-col gap-2 p-3 rounded-2xl bg-white border border-amber-100/50 shadow-sm transition-all hover:shadow-md">
            <div className="flex items-center gap-3">
                <div className="h-2 w-2 rounded-full bg-amber-200 flex-shrink-0" />
            
            {currentQty !== null && (
                <Popover>
                    <PopoverTrigger asChild>
                        <button className={cn(
                            "text-sm font-bold text-amber-900 bg-amber-50 px-2 py-1 rounded-lg hover:bg-amber-100 transition-colors",
                            isConverting && "opacity-50 animate-pulse"
                        )}>
                            {formatQtyLocal(currentQty, { rounding: prefs?.rounding, decimals: prefs?.decimal_places })} <span className="text-xs font-normal text-amber-700">{currentUnit}</span>
                        </button>
                    </PopoverTrigger>
                    <PopoverContent className="w-40 p-2 z-[150]">
                        <div className="grid gap-1">
                            <p className="text-[10px] font-bold text-stone-400 uppercase tracking-widest mb-1">Convert To</p>
                            {sortedUnits.map(u => (
                                <button 
                                    key={u}
                                    onClick={() => handleUnitSelect(u)}
                                    className="text-left text-sm px-2 py-1.5 hover:bg-stone-50 rounded-md text-stone-700 font-medium"
                                >
                                    {u}
                                </button>
                            ))}
                            <button 
                                onClick={() => {
                                    setCurrentQty(originalQty);
                                    setCurrentUnit(originalUnit);
                                }}
                                className="text-left text-sm px-2 py-1.5 hover:bg-stone-50 rounded-md text-stone-500 italic mt-1 border-t"
                            >
                                Reset
                            </button>
                        </div>
                    </PopoverContent>
                </Popover>
            )}

            <span className="text-sm font-medium text-stone-700 flex-1">{ingredient.name}</span>
            </div>
            
            {densityNeeded && (
                <div className="flex items-center gap-2 p-2 bg-amber-50/80 rounded-lg text-xs animate-in slide-in-from-top-1">
                    <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0" />
                    <span className="flex-1 text-amber-900 font-medium">Density needed for accurate conversion</span>
                    <Input 
                        className="h-7 w-20 text-xs bg-white border-amber-200"
                        placeholder="g / cup"
                        value={densityValue}
                        onChange={e => setDensityValue(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSaveDensity()}
                    />
                    <Button size="sm" onClick={handleSaveDensity} disabled={isSavingDensity} className="h-7 text-[10px] bg-amber-600 hover:bg-amber-700">
                        Save
                    </Button>
                </div>
            )}
        </div>
    );
}
