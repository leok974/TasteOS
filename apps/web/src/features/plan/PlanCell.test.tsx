
import { render, screen } from '@testing-library/react';
import { PlanCell } from './PlanCell';
import { describe, it, expect, vi } from 'vitest';

// Mock hook
vi.mock('./hooks', () => ({
  useUpdateEntry: () => ({ updateEntry: vi.fn() }),
}));

// Mock SwapModal to avoid deeper renders/logic
vi.mock('./SwapRecipeModal', () => ({
  SwapRecipeModal: () => <div data-testid="swap-modal" />
}));

describe('PlanCell', () => {
  it('renders without "Nonem" when time is null', () => {
    const entry = {
        id: '1', date: '2025-01-01', meal_type: 'dinner', is_leftover: false,
        recipe_title: 'Valid Recipe', 
        recipe_total_minutes: null, // explicit null
        method_choice: 'Stove', method_options_json: {}
    };
    render(<PlanCell entry={entry as any} type="dinner" />);
    
    // Should verify lack of time pill content or text "Nonem"
    const content = screen.queryByText(/Nonem/);
    expect(content).not.toBeInTheDocument();
    
    // Also ensure no empty "m" or similar
    expect(screen.queryByText(/⏱/)).not.toBeInTheDocument();
  });

   it('renders formatted time when valid', () => {
    const entry = {
        id: '1', date: '2025-01-01', meal_type: 'dinner', is_leftover: false,
        recipe_title: 'Valid Recipe', 
        recipe_total_minutes: 60,
        method_choice: 'Stove', method_options_json: {}
    };
    render(<PlanCell entry={entry as any} type="dinner" />);
    expect(screen.getByText('⏱ 60m')).toBeInTheDocument();
  });
  
  it('sanitizes leading hash in title', () => {
      const entry = {
        id: '1', date: '2025-01-01', meal_type: 'dinner', is_leftover: false,
        recipe_title: '# Chipotle-Style Bowl', 
        recipe_total_minutes: 60,
        method_choice: 'Stove', method_options_json: {}
    };
    render(<PlanCell entry={entry as any} type="dinner" />);
    
    // Should find cleaned title
    expect(screen.getByText('Chipotle-Style Bowl')).toBeInTheDocument();
    // Should not find raw title
    expect(screen.queryByText('# Chipotle-Style Bowl')).not.toBeInTheDocument();
  });

  it('uses flex-wrap and min-w-0 for layout', () => {
      const entry = {
        id: '1', date: '2025-01-01', meal_type: 'dinner', is_leftover: false,
        recipe_title: 'Recipe', 
        recipe_total_minutes: 60,
        method_choice: 'Stove', // Renders a badge
        method_options_json: {}
    };
    const { container } = render(<PlanCell entry={entry as any} type="dinner" />);
    
    // Locate the tags container
    // We look for the div containing the badge
    const badge = screen.getByText('Stove').closest('.flex');
    expect(badge).toHaveClass('flex-wrap');
    expect(badge).toHaveClass('min-w-0');
  });
});
