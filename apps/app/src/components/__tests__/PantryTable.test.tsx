/**
 * Tests for PantryTable component
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PantryTable } from '../PantryTable';
import type { PantryItem } from '../../lib/api';

describe('PantryTable', () => {
  it('renders empty state when no items', () => {
    render(<PantryTable items={[]} onItemDeleted={() => {}} />);
    expect(screen.getByText(/your pantry is empty/i)).toBeInTheDocument();
  });

  it('renders pantry items', () => {
    const items: PantryItem[] = [
      {
        id: '1',
        user_id: 'user1',
        name: 'Chicken Breast',
        quantity: 2,
        unit: 'lbs',
        expires_at: null,
        tags: ['meat', 'protein'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<PantryTable items={items} onItemDeleted={() => {}} />);
    expect(screen.getByText('Chicken Breast')).toBeInTheDocument();
    expect(screen.getByText('2 lbs')).toBeInTheDocument();
  });

  it('shows expiring soon badge', () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);

    const items: PantryItem[] = [
      {
        id: '2',
        user_id: 'user1',
        name: 'Milk',
        quantity: 1,
        unit: 'gallon',
        expires_at: tomorrow.toISOString(),
        tags: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<PantryTable items={items} onItemDeleted={() => {}} />);
    expect(screen.getByText(/expiring soon/i)).toBeInTheDocument();
  });

  it('shows low stock badge', () => {
    const items: PantryItem[] = [
      {
        id: '3',
        user_id: 'user1',
        name: 'Eggs',
        quantity: 0.5,
        unit: 'dozen',
        expires_at: null,
        tags: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(<PantryTable items={items} onItemDeleted={() => {}} />);
    expect(screen.getByText(/low/i)).toBeInTheDocument();
  });
});
