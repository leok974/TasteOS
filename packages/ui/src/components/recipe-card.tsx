import * as React from 'react'
import type { Recipe } from '@tasteos/types'

interface RecipeCardProps {
  recipe: Recipe
  onSelect?: (recipe: Recipe) => void
  onFavorite?: (recipe: Recipe) => void
  variant?: 'default' | 'compact'
}

export function RecipeCard({
  recipe,
  onSelect,
  onFavorite,
  variant = 'default'
}: RecipeCardProps) {
  return (
    <div className="bg-card border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer">
      <div className="aspect-video bg-muted rounded-md mb-3">
        {recipe.images?.[0] && (
          <img
            src={recipe.images[0]}
            alt={recipe.title}
            className="w-full h-full object-cover rounded-md"
          />
        )}
      </div>

      <div className="space-y-2">
        <h3 className="font-semibold text-lg line-clamp-1">{recipe.title}</h3>
        <p className="text-muted-foreground text-sm line-clamp-2">{recipe.description}</p>

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{recipe.totalTime} min</span>
          <span>{recipe.servings} servings</span>
          <span className="capitalize">{recipe.difficulty}</span>
        </div>

        <div className="flex flex-wrap gap-1">
          {recipe.tags.slice(0, 3).map(tag => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-secondary text-secondary-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
