/**
 * Recipe detail page with tabs
 *
 * Shows Base recipe, Variants, and Nutrition (stubbed)
 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import type { Recipe, RecipeVariant } from '@tasteos/types';
import { getRecipe, getRecipeVariants } from '../lib/api';
import { RecipeDetail } from '../components/RecipeDetail';
import { VariantPanel } from '../components/VariantPanel';
import { NutritionPanel } from '../components/NutritionPanel';

type Tab = 'base' | 'variants' | 'nutrition';

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [variants, setVariants] = useState<RecipeVariant[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('base');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadRecipeData(id);
    }
  }, [id]);

  const loadRecipeData = async (recipeId: string) => {
    try {
      setLoading(true);
      const [recipeData, variantsData] = await Promise.all([
        getRecipe(recipeId),
        getRecipeVariants(recipeId),
      ]);
      setRecipe(recipeData);
      setVariants(variantsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipe');
    } finally {
      setLoading(false);
    }
  };

  const handleVariantGenerated = (variant: RecipeVariant) => {
    setVariants(prev => [...prev, variant]);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">Loading recipe...</div>
        </div>
      </div>
    );
  }

  if (error || !recipe) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error || 'Recipe not found'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'base', label: 'Base Recipe' },
            { id: 'variants', label: `Variants (${variants.length})` },
            { id: 'nutrition', label: 'Nutrition' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as Tab)}
              className={`
                py-4 px-1 border-b-2 font-medium text-sm
                ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'base' && <RecipeDetail recipe={recipe} />}

      {activeTab === 'variants' && (
        <VariantPanel
          recipe={recipe}
          variants={variants}
          onVariantGenerated={handleVariantGenerated}
        />
      )}

      {activeTab === 'nutrition' && (
        <NutritionPanel recipeId={recipe.id} />
      )}
    </div>
  );
}
