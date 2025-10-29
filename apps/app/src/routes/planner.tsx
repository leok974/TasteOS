/**
 * Meal Planner page
 *
 * Generate and view weekly meal plans
 */

import { useState } from 'react';
import { generateMealPlan, getTodayPlan, type MealPlan, type GeneratePlanOptions } from '../lib/api';
import { PlannerView } from '../components/PlannerView';
import { Button } from '@tasteos/ui';
import { CalendarDays, Loader2, Sparkles, TrendingUp } from 'lucide-react';

export function PlannerPage() {
  const [plans, setPlans] = useState<MealPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Form state
  const [days, setDays] = useState('7');
  const [calorieGoal, setCalorieGoal] = useState('2000');
  const [proteinGoal, setProteinGoal] = useState('150');
  const [preferences, setPreferences] = useState('');

  const loadTodayPlan = async () => {
    try {
      setLoading(true);
      setError(null);
      const plan = await getTodayPlan();
      if (plan) {
        setPlans([plan]);
      } else {
        setPlans([]);
      }
    } catch (err: any) {
      console.error('[TasteOS][Planner] failed to load today\'s plan:', err);
      setError(err.message || 'Failed to load meal plan');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      setError(null);

      const options: GeneratePlanOptions = {
        days: parseInt(days, 10),
        goals: {
          calories: parseInt(calorieGoal, 10),
          protein_g: parseInt(proteinGoal, 10),
        },
        dietary_preferences: preferences.trim() ? preferences.split(',').map(p => p.trim()) : [],
      };

      const response = await generateMealPlan(options);

      // Load the generated plans
      if (response.plan_ids && response.plan_ids.length > 0) {
        // For simplicity, just fetch today's plan after generation
        // In production, you might fetch all generated plans by ID
        await loadTodayPlan();
      } else {
        setError('No plans were generated');
      }
    } catch (err: any) {
      console.error('[TasteOS][Planner] failed to generate meal plan:', err);
      setError(err.message || 'Failed to generate meal plan');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <CalendarDays className="w-8 h-8" />
          Meal Planner
        </h1>
        <p className="text-gray-600 mt-1">
          Generate personalized meal plans based on your pantry and goals
        </p>
      </div>

      {/* Generate Form */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-500" />
          Generate New Plan
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label htmlFor="days" className="block text-sm font-medium text-gray-700 mb-1">
              Number of Days
            </label>
            <input
              id="days"
              type="number"
              min="1"
              max="14"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="calories" className="block text-sm font-medium text-gray-700 mb-1">
              Daily Calorie Goal
            </label>
            <input
              id="calories"
              type="number"
              min="1000"
              max="5000"
              step="100"
              value={calorieGoal}
              onChange={(e) => setCalorieGoal(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="protein" className="block text-sm font-medium text-gray-700 mb-1">
              Protein Goal (g)
            </label>
            <input
              id="protein"
              type="number"
              min="50"
              max="300"
              step="10"
              value={proteinGoal}
              onChange={(e) => setProteinGoal(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="flex items-end">
            <Button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Generate
                </>
              )}
            </Button>
          </div>
        </div>

        <div>
          <label htmlFor="preferences" className="block text-sm font-medium text-gray-700 mb-1">
            Dietary Preferences (optional)
          </label>
          <textarea
            id="preferences"
            value={preferences}
            onChange={(e) => setPreferences(e.target.value)}
            placeholder="e.g., vegetarian, low-carb, no dairy, etc."
            rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-3 text-gray-600">Loading plans...</span>
        </div>
      )}

      {/* Plans */}
      {!loading && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Your Meal Plans</h2>
            <Button onClick={loadTodayPlan} variant="outline" size="sm">
              Load Today's Plan
            </Button>
          </div>
          <PlannerView plans={plans} />
        </div>
      )}
    </div>
  );
}
