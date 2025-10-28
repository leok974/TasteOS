/**
 * RecipeDetail component
 *
 * Displays recipe information including ingredients and instructions
 */

import type { Recipe, Ingredient, Instruction } from '@tasteos/types';
import { Clock, Users, ChefHat } from 'lucide-react';

interface RecipeDetailProps {
  recipe: Recipe;
}

export function RecipeDetail({ recipe }: RecipeDetailProps) {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-gray-900 mb-2">{recipe.title}</h1>
        <p className="text-lg text-gray-600">{recipe.description}</p>
      </div>

      {/* Metadata */}
      <div className="flex flex-wrap gap-6 py-4 border-y border-gray-200">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-400" />
          <span className="text-sm">
            <span className="font-medium">Prep:</span> {recipe.prepTime}min
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-400" />
          <span className="text-sm">
            <span className="font-medium">Cook:</span> {recipe.cookTime}min
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-gray-400" />
          <span className="text-sm">
            <span className="font-medium">Servings:</span> {recipe.servings}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <ChefHat className="w-5 h-5 text-gray-400" />
          <span className="text-sm capitalize">
            <span className="font-medium">Difficulty:</span> {recipe.difficulty}
          </span>
        </div>
        {recipe.cuisine && (
          <div className="text-sm">
            <span className="font-medium">Cuisine:</span> {recipe.cuisine}
          </div>
        )}
      </div>

      {/* Tags */}
      {recipe.tags && recipe.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {recipe.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Ingredients */}
        <div className="lg:col-span-1">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Ingredients</h2>
          <div className="bg-gray-50 rounded-lg p-6">
            <ul className="space-y-3">
              {recipe.ingredients.map((ingredient: Ingredient) => (
                <li key={ingredient.id} className="flex items-start">
                  <span className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3" />
                  <div className="flex-1">
                    <span className="font-medium">
                      {ingredient.amount} {ingredient.unit}
                    </span>{' '}
                    <span>{ingredient.name}</span>
                    {ingredient.preparation && (
                      <span className="text-gray-600 text-sm">
                        {' '}({ingredient.preparation})
                      </span>
                    )}
                    {ingredient.optional && (
                      <span className="text-gray-500 text-sm italic"> (optional)</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Instructions */}
        <div className="lg:col-span-2">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Instructions</h2>
          <div className="space-y-6">
            {recipe.instructions.map((instruction: Instruction) => (
              <div key={instruction.id} className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-semibold">
                  {instruction.stepNumber}
                </div>
                <div className="flex-1 pt-1">
                  <p className="text-gray-900">{instruction.description}</p>
                  {instruction.duration && (
                    <p className="text-sm text-gray-500 mt-1">
                      ⏱️ {instruction.duration} minutes
                    </p>
                  )}
                  {instruction.temperature && (
                    <p className="text-sm text-gray-500 mt-1">
                      🌡️ {instruction.temperature}°C
                    </p>
                  )}
                  {instruction.tips && instruction.tips.length > 0 && (
                    <div className="mt-2 text-sm text-blue-600">
                      💡 Tip: {instruction.tips.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
