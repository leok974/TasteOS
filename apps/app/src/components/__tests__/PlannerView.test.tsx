/**
 * Tests for PlannerView component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlannerView } from '../components/PlannerView';
import type { MealPlan } from '../lib/api';

describe('PlannerView', () => {
  it('renders empty state when no plans', () => {
    render(<PlannerView plans={[]} />);
    expect(screen.getByText(/no meal plans yet/i)).toBeInTheDocument();
  });

  it('renders meal plan cards', () => {
    const plans: MealPlan[] = [
      {
        id: '1',
        user_id: 'user1',
        date: new Date().toISOString().split('T')[0],
        breakfast: [{ recipe_id: null, title: 'Oatmeal' }],
        lunch: [{ recipe_id: null, title: 'Salad' }],
        dinner: [{ recipe_id: null, title: 'Pasta' }],
        snacks: [],
        total_calories: 1800,
        total_protein_g: 70,
        total_carbs_g: 200,
        total_fat_g: 50,
        notes: null,
        plan_batch_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<PlannerView plans={plans} />);
    expect(screen.getByText('Oatmeal')).toBeInTheDocument();
    expect(screen.getByText('Salad')).toBeInTheDocument();
    expect(screen.getByText('Pasta')).toBeInTheDocument();
    expect(screen.getByText('1800 cal')).toBeInTheDocument();
  });

  it('renders nutrition information', () => {
    const plans: MealPlan[] = [
      {
        id: '2',
        user_id: 'user1',
        date: new Date().toISOString().split('T')[0],
        breakfast: [{ recipe_id: null, title: 'Eggs' }],
        lunch: [],
        dinner: [],
        snacks: [],
        total_calories: 2000,
        total_protein_g: 150,
        total_carbs_g: 180,
        total_fat_g: 60,
        notes: null,
        plan_batch_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<PlannerView plans={plans} />);
    expect(screen.getByText(/150g protein/i)).toBeInTheDocument();
    expect(screen.getByText(/180g carbs/i)).toBeInTheDocument();
    expect(screen.getByText(/60g fat/i)).toBeInTheDocument();
  });
});
