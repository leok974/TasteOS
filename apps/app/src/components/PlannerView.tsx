/**
 * PlannerView component
 *
 * Display weekly meal plans with nutrition info
 */

import type { MealPlan } from '../lib/api';
import { Calendar, Utensils, Coffee, Sandwich, Cookie } from 'lucide-react';
import { Badge } from '@tasteos/ui';

interface PlannerViewProps {
  plans: MealPlan[];
}

export function PlannerView({ plans }: PlannerViewProps) {
  if (plans.length === 0) {
    return (
      <div className="text-center py-12">
        <Calendar className="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No meal plans yet</h3>
        <p className="text-gray-600">
          Generate a meal plan to see your weekly schedule
        </p>
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const getMealIcon = (mealType: string) => {
    switch (mealType) {
      case 'breakfast':
        return <Coffee className="w-4 h-4" />;
      case 'lunch':
        return <Sandwich className="w-4 h-4" />;
      case 'dinner':
        return <Utensils className="w-4 h-4" />;
      case 'snacks':
        return <Cookie className="w-4 h-4" />;
      default:
        return <Utensils className="w-4 h-4" />;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {plans.map((plan) => (
        <div key={plan.id} className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4">
            <div className="flex items-center gap-2 mb-1">
              <Calendar className="w-5 h-5" />
              <h3 className="font-semibold">{formatDate(plan.date)}</h3>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <span className="font-medium">{plan.total_calories || 0} cal</span>
              {plan.total_protein_g && (
                <span className="text-blue-100">{plan.total_protein_g}g protein</span>
              )}
            </div>
          </div>

          {/* Meals */}
          <div className="p-4 space-y-3">
            {/* Breakfast */}
            {plan.breakfast && plan.breakfast.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  {getMealIcon('breakfast')}
                  <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Breakfast</span>
                </div>
                <div className="space-y-1">
                  {plan.breakfast.map((recipe, idx) => (
                    <div key={idx} className="text-sm text-gray-800 pl-6">
                      {recipe.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Lunch */}
            {plan.lunch && plan.lunch.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  {getMealIcon('lunch')}
                  <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Lunch</span>
                </div>
                <div className="space-y-1">
                  {plan.lunch.map((recipe, idx) => (
                    <div key={idx} className="text-sm text-gray-800 pl-6">
                      {recipe.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Dinner */}
            {plan.dinner && plan.dinner.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  {getMealIcon('dinner')}
                  <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Dinner</span>
                </div>
                <div className="space-y-1">
                  {plan.dinner.map((recipe, idx) => (
                    <div key={idx} className="text-sm text-gray-800 pl-6">
                      {recipe.title}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Snacks */}
            {plan.snacks && plan.snacks.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  {getMealIcon('snacks')}
                  <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Snacks</span>
                </div>
                <div className="space-y-1">
                  {plan.snacks.map((recipe, idx) => (
                    <div key={idx} className="text-sm text-gray-800 pl-6">
                      {recipe.title}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer - Macros */}
          {(plan.total_carbs_g || plan.total_fat_g) && (
            <div className="border-t border-gray-100 px-4 py-2 bg-gray-50 flex gap-3 text-xs">
              {plan.total_carbs_g && (
                <Badge variant="outline" className="text-amber-700 border-amber-200 bg-amber-50">
                  {plan.total_carbs_g}g carbs
                </Badge>
              )}
              {plan.total_fat_g && (
                <Badge variant="outline" className="text-green-700 border-green-200 bg-green-50">
                  {plan.total_fat_g}g fat
                </Badge>
              )}
            </div>
          )}

          {/* Notes */}
          {plan.notes && (
            <div className="px-4 pb-3">
              <p className="text-xs text-gray-600 italic">{plan.notes}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
