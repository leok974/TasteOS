/**
 * Recipes list page
 *
 * Shows grid of all user's recipes with links to detail pages
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Recipe } from '@tasteos/types';
import { getRecipes } from '../lib/api';
import { RecipeCard } from '@tasteos/ui';

export function Recipes() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRecipes();
  }, []);

  const loadRecipes = async () => {
    try {
      setLoading(true);
      const data = await getRecipes();
      setRecipes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipes');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">Loading recipes...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">My Recipes</h1>
        <p className="mt-2 text-gray-600">
          {recipes.length} recipe{recipes.length !== 1 ? 's' : ''} in your cookbook
        </p>
      </div>

      {recipes.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-600 mb-4">No recipes yet!</p>
          <p className="text-sm text-gray-500">
            Create your first recipe to get started
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recipes.map((recipe) => (
            <Link key={recipe.id} to={`/recipes/${recipe.id}`}>
              <RecipeCard recipe={recipe} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
