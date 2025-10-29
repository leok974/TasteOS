/**
 * NutritionBar component
 *
 * Visual bars showing % daily value for protein, carbs, fat
 */

export interface NutritionBarProps {
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  className?: string;
}

export function NutritionBar({
  calories,
  protein,
  carbs,
  fat,
  className = '',
}: NutritionBarProps) {
  // Calculate percentages for visual representation
  const totalMacros = protein * 4 + carbs * 4 + fat * 9; // calories from macros
  const proteinPct = ((protein * 4) / totalMacros) * 100;
  const carbsPct = ((carbs * 4) / totalMacros) * 100;
  const fatPct = ((fat * 9) / totalMacros) * 100;

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Total Calories */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Calories</span>
        <span className="text-lg font-bold text-gray-900">{calories}</span>
      </div>

      {/* Macros Bar Chart */}
      <div className="h-3 flex rounded-full overflow-hidden bg-gray-200">
        <div
          className="bg-blue-500 transition-all"
          style={{ width: `${proteinPct}%` }}
          title={`Protein: ${proteinPct.toFixed(0)}%`}
        />
        <div
          className="bg-green-500 transition-all"
          style={{ width: `${carbsPct}%` }}
          title={`Carbs: ${carbsPct.toFixed(0)}%`}
        />
        <div
          className="bg-yellow-500 transition-all"
          style={{ width: `${fatPct}%` }}
          title={`Fat: ${fatPct.toFixed(0)}%`}
        />
      </div>

      {/* Macro Details */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="flex items-center gap-1 mb-1">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-gray-600">Protein</span>
          </div>
          <div className="font-semibold">{protein}g</div>
        </div>
        <div>
          <div className="flex items-center gap-1 mb-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-gray-600">Carbs</span>
          </div>
          <div className="font-semibold">{carbs}g</div>
        </div>
        <div>
          <div className="flex items-center gap-1 mb-1">
            <div className="w-2 h-2 rounded-full bg-yellow-500" />
            <span className="text-gray-600">Fat</span>
          </div>
          <div className="font-semibold">{fat}g</div>
        </div>
      </div>
    </div>
  );
}
