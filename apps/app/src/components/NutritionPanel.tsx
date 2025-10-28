/**
 * Nutrition Panel Component
 *
 * Displays nutritional information for a recipe
 */

import { useState, useEffect } from 'react';
import { NutritionBar, MacroBadge } from '@tasteos/ui';
import { getRecipeNutrition, getVariantNutrition } from '../lib/api';

interface NutritionData {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  notes?: string | null;
}

interface NutritionPanelProps {
  recipeId: string;
  variantId?: string;
}

export function NutritionPanel({ recipeId, variantId }: NutritionPanelProps) {
  const [nutrition, setNutrition] = useState<NutritionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchNutrition() {
      setLoading(true);
      setError(null);

      try {
        const data = variantId
          ? await getVariantNutrition(variantId)
          : await getRecipeNutrition(recipeId);

        setNutrition(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load nutrition');
      } finally {
        setLoading(false);
      }
    }

    fetchNutrition();
  }, [recipeId, variantId]);

  if (loading) {
    return (
      <div className="p-6 space-y-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3" />
        <div className="h-12 bg-gray-200 rounded" />
        <div className="grid grid-cols-3 gap-4">
          <div className="h-16 bg-gray-200 rounded" />
          <div className="h-16 bg-gray-200 rounded" />
          <div className="h-16 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800 text-sm">
            Nutrition data not available yet. {error}
          </p>
        </div>
      </div>
    );
  }

  if (!nutrition) {
    return null;
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-1">Nutritional Information</h3>
        <p className="text-sm text-gray-600">Per serving</p>
      </div>

      <NutritionBar
        calories={nutrition.calories}
        protein={nutrition.protein_g}
        carbs={nutrition.carbs_g}
        fat={nutrition.fat_g}
      />

      {nutrition.notes && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-900">{nutrition.notes}</p>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <MacroBadge
          label="calories"
          value={nutrition.calories}
          unit=" kcal"
          variant="calories"
        />
        <MacroBadge
          label="protein"
          value={nutrition.protein_g}
          variant="protein"
        />
        <MacroBadge
          label="carbs"
          value={nutrition.carbs_g}
          variant="carbs"
        />
        <MacroBadge
          label="fat"
          value={nutrition.fat_g}
          variant="fat"
        />
      </div>
    </div>
  );
}
