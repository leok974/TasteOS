/**
 * VariantPanel component
 *
 * Manages AI variant generation with quota display and PlanGuard
 */

import { useState, useEffect } from 'react';
import type { Recipe, RecipeVariant } from '@tasteos/types';
import { useVariants } from '../lib/useVariants';
import { getBillingPlan, getRecipeNutrition, getVariantNutrition } from '../lib/api';
import { canGenerateVariant, formatQuotaDisplay } from '../lib/planLimits';
import { Button, PlanGuard, MacroBadge } from '@tasteos/ui';
import { DiffView } from './DiffView';
import { VariantApproveButton } from './VariantApproveButton';
import { Sparkles, AlertCircle } from 'lucide-react';

interface VariantPanelProps {
  recipe: Recipe;
  variants: RecipeVariant[];
  onVariantGenerated: (variant: RecipeVariant) => void;
}

type VariantType = 'dietary' | 'cuisine' | 'substitution' | 'simplify' | 'upscale';

export function VariantPanel({ recipe, variants, onVariantGenerated }: VariantPanelProps) {
  const { generate, loading, error, quotaError, clearError } = useVariants(recipe.id);
  const [plan, setPlan] = useState<any>(null);
  const [selectedVariantType, setSelectedVariantType] = useState<VariantType>('dietary');
  const [dietaryRestriction, setDietaryRestriction] = useState('');
  const [targetCuisine, setTargetCuisine] = useState('');
  const [selectedVariantForDiff, setSelectedVariantForDiff] = useState<string | null>(null);
  const [baseNutrition, setBaseNutrition] = useState<any>(null);
  const [variantNutrition, setVariantNutrition] = useState<Record<string, any>>({});

  useEffect(() => {
    loadBillingPlan();
    loadBaseNutrition();
  }, []);

  useEffect(() => {
    // Load nutrition for all variants
    variants.forEach(variant => {
      if (!variantNutrition[variant.id]) {
        loadVariantNutrition(variant.id);
      }
    });
  }, [variants]);

  const loadBaseNutrition = async () => {
    try {
      const data = await getRecipeNutrition(recipe.id);
      setBaseNutrition(data);
    } catch (err) {
      console.error('[TasteOS][VariantPanel] failed to load base nutrition:', err);
    }
  };

  const loadVariantNutrition = async (variantId: string) => {
    try {
      const data = await getVariantNutrition(variantId);
      setVariantNutrition(prev => ({ ...prev, [variantId]: data }));
    } catch (err) {
      console.error(`[TasteOS][VariantPanel] failed to load nutrition for variant ${variantId}:`, err);
    }
  };

  const loadBillingPlan = async () => {
    try {
      const data = await getBillingPlan();
      setPlan(data);
    } catch (err) {
      console.error('[TasteOS][VariantPanel] failed to load billing plan:', err);
    }
  };

  const handleGenerate = async () => {
    clearError();

    const options: any = {};
    if (selectedVariantType === 'dietary' && dietaryRestriction) {
      options.dietary_restriction = dietaryRestriction;
    }
    if (selectedVariantType === 'cuisine' && targetCuisine) {
      options.target_cuisine = targetCuisine;
    }

    const variant = await generate(recipe.id, selectedVariantType, options);
    if (variant) {
      onVariantGenerated(variant);
      // Refresh billing plan to update quota
      await loadBillingPlan();
    }
  };

  const canGenerate = plan && canGenerateVariant(plan.plan, plan.dailyVariantQuotaUsed);

  return (
    <div className="space-y-8">
      {/* Quota Display */}
      {plan && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-900">
                {formatQuotaDisplay(plan.plan, plan.dailyVariantQuotaUsed)}
              </p>
              <p className="text-xs text-blue-700 mt-1">
                Resets daily. Current plan: <span className="font-medium capitalize">{plan.plan}</span>
              </p>
            </div>
            {plan.limits.remaining < 2 && plan.plan === 'free' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.location.href = '/settings/billing'}
              >
                Upgrade
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && !quotaError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-900">Generation Failed</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Generation Form */}
      {canGenerate ? (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-500" />
            Generate New Variant
          </h3>

          <div className="space-y-4">
            {/* Variant Type Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Variant Type
              </label>
              <select
                value={selectedVariantType}
                onChange={(e) => setSelectedVariantType(e.target.value as VariantType)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              >
                <option value="dietary">Dietary Adaptation</option>
                <option value="cuisine">Cuisine Transform</option>
                <option value="substitution">Ingredient Substitution</option>
                <option value="simplify">Simplify Recipe</option>
                <option value="upscale">Upscale/Gourmet</option>
              </select>
            </div>

            {/* Dietary Restriction Input */}
            {selectedVariantType === 'dietary' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dietary Restriction
                </label>
                <input
                  type="text"
                  value={dietaryRestriction}
                  onChange={(e) => setDietaryRestriction(e.target.value)}
                  placeholder="e.g., vegan, gluten-free, low-carb"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
              </div>
            )}

            {/* Cuisine Input */}
            {selectedVariantType === 'cuisine' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Target Cuisine
                </label>
                <input
                  type="text"
                  value={targetCuisine}
                  onChange={(e) => setTargetCuisine(e.target.value)}
                  placeholder="e.g., Italian, Japanese, Mexican"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
              </div>
            )}

            <Button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <>
                  <span className="animate-spin mr-2">⚙️</span>
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate Variant
                </>
              )}
            </Button>
          </div>
        </div>
      ) : (
        <PlanGuard
          plan={plan?.plan || 'free'}
          featureName="daily variant generation"
        >
          <p className="text-sm text-gray-500">
            Upgrade to Pro for 30 variants/day or Enterprise for 60 variants/day.
          </p>
        </PlanGuard>
      )}

      {/* Variants List */}
      <div>
        <h3 className="text-xl font-semibold text-gray-900 mb-4">
          Generated Variants ({variants.length})
        </h3>

        {variants.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
            <p className="text-gray-600">No variants generated yet</p>
            <p className="text-sm text-gray-500 mt-1">
              Click "Generate Variant" above to create your first variant
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {variants.map((variant) => (
              <div
                key={variant.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900">{variant.title}</h4>
                    <p className="text-sm text-gray-600 mt-1">{variant.description}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800 capitalize">
                        {variant.variantType}
                      </span>
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-800 capitalize">
                        {variant.status}
                      </span>
                    </div>

                    {/* Nutrition Deltas */}
                    {baseNutrition && variantNutrition[variant.id] && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {(() => {
                          const vNutr = variantNutrition[variant.id];
                          const calDelta = vNutr.calories - baseNutrition.calories;
                          const proteinDelta = vNutr.protein_g - baseNutrition.protein_g;
                          const carbsDelta = vNutr.carbs_g - baseNutrition.carbs_g;
                          const fatDelta = vNutr.fat_g - baseNutrition.fat_g;

                          return (
                            <>
                              {calDelta !== 0 && (
                                <MacroBadge
                                  label="kcal"
                                  value={calDelta > 0 ? `+${calDelta}` : calDelta}
                                  unit=""
                                  variant="calories"
                                  className="text-xs"
                                />
                              )}
                              {proteinDelta !== 0 && (
                                <MacroBadge
                                  label={`protein ${proteinDelta > 0 ? '💪' : ''}`}
                                  value={proteinDelta > 0 ? `+${proteinDelta.toFixed(1)}` : proteinDelta.toFixed(1)}
                                  unit="g"
                                  variant="protein"
                                  className="text-xs"
                                />
                              )}
                              {carbsDelta !== 0 && (
                                <MacroBadge
                                  label="carbs"
                                  value={carbsDelta > 0 ? `+${carbsDelta.toFixed(1)}` : carbsDelta.toFixed(1)}
                                  unit="g"
                                  variant="carbs"
                                  className="text-xs"
                                />
                              )}
                              {fatDelta !== 0 && (
                                <MacroBadge
                                  label="fat"
                                  value={fatDelta > 0 ? `+${fatDelta.toFixed(1)}` : fatDelta.toFixed(1)}
                                  unit="g"
                                  variant="fat"
                                  className="text-xs"
                                />
                              )}
                            </>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                  <VariantApproveButton
                    variantId={variant.id}
                    isApproved={variant.status === 'approved'}
                  />
                </div>

                {variant.metadata && (
                  <div className="text-sm text-gray-600 mt-3">
                    <p>
                      <span className="font-medium">Confidence:</span>{' '}
                      {Math.round((variant.metadata.confidenceScore || 0) * 100)}%
                    </p>
                  </div>
                )}

                <div className="mt-3 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedVariantForDiff(
                      selectedVariantForDiff === variant.id ? null : variant.id
                    )}
                  >
                    {selectedVariantForDiff === variant.id ? 'Hide' : 'View'} Diff
                  </Button>
                </div>

                {selectedVariantForDiff === variant.id && (
                  <div className="mt-4">
                    <DiffView variantId={variant.id} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
