/**
 * Tests for ShoppingList component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ShoppingList } from '../components/ShoppingList';
import type { GroceryItem } from '../lib/api';

// Mock the API module
vi.mock('../lib/api', () => ({
  togglePurchased: vi.fn(() => Promise.resolve()),
}));

describe('ShoppingList', () => {
  it('renders empty state when no items', () => {
    render(<ShoppingList items={[]} onItemToggled={() => {}} />);
    expect(screen.getByText(/shopping list is empty/i)).toBeInTheDocument();
  });

  it('renders unpurchased items', () => {
    const items: GroceryItem[] = [
      {
        id: '1',
        user_id: 'user1',
        meal_plan_id: 'plan1',
        name: 'Tomatoes',
        quantity: 4,
        unit: 'count',
        purchased: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<ShoppingList items={items} onItemToggled={() => {}} />);
    expect(screen.getByText('Tomatoes')).toBeInTheDocument();
    expect(screen.getByText('4 count')).toBeInTheDocument();
    expect(screen.getByText(/to buy/i)).toBeInTheDocument();
  });

  it('renders purchased items with strikethrough', () => {
    const items: GroceryItem[] = [
      {
        id: '2',
        user_id: 'user1',
        meal_plan_id: 'plan1',
        name: 'Bread',
        quantity: 1,
        unit: 'loaf',
        purchased: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<ShoppingList items={items} onItemToggled={() => {}} />);
    expect(screen.getByText('Bread')).toBeInTheDocument();
    expect(screen.getByText(/purchased/i)).toBeInTheDocument();
  });

  it('separates purchased and unpurchased items', () => {
    const items: GroceryItem[] = [
      {
        id: '1',
        user_id: 'user1',
        meal_plan_id: 'plan1',
        name: 'Eggs',
        quantity: 12,
        unit: 'count',
        purchased: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: '2',
        user_id: 'user1',
        meal_plan_id: 'plan1',
        name: 'Milk',
        quantity: 1,
        unit: 'gallon',
        purchased: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<ShoppingList items={items} onItemToggled={() => {}} />);
    expect(screen.getByText(/to buy \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/purchased \(1\)/i)).toBeInTheDocument();
  });
});
