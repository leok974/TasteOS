import { render, screen, fireEvent } from '@testing-library/react';
import { NextUpPanel } from '../NextUpPanel';
import { useCookNext, useCookSessionPatch, useCookTimerAction, useCookTimerCreate, useCookSessionEnd } from '../../hooks';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../hooks', () => ({
    useCookNext: vi.fn(),
    useCookSessionPatch: vi.fn(),
    useCookTimerCreate: vi.fn(),
    useCookTimerAction: vi.fn(),
    useCookSessionEnd: vi.fn(),
    CookSession: {}
}));

const mockSession = {
    id: 's1',
    recipe_id: 'r1',
    status: 'active',
    current_step_index: 0,
    step_checks: {},
    timers: {}
};

const mockRecipe = {
    steps: [
        { step_index: 0, title: 'Step 1', bullets: ['b1', 'b2'] },
        { step_index: 1, title: 'Step 2' }
    ]
};

describe('NextUpPanel', () => {
    const mockPatch = vi.fn();
    const mockCreateTimer = vi.fn();
    const mockTimerAction = vi.fn();
    
    beforeEach(() => {
        vi.clearAllMocks();
        (useCookSessionPatch as any).mockReturnValue({ mutate: mockPatch });
        (useCookTimerCreate as any).mockReturnValue({ mutate: mockCreateTimer });
        (useCookTimerAction as any).mockReturnValue({ mutate: mockTimerAction });
        (useCookSessionEnd as any).mockReturnValue({ mutate: vi.fn() });
    });

    it('renders suggested action', () => {
        (useCookNext as any).mockReturnValue({
            data: {
                suggested_step_idx: 0,
                actions: [{ type: 'mark_step_done', label: 'Mark Done', step_idx: 0 }],
                reason: 'Test'
            },
            isLoading: false
        });

        render(<NextUpPanel session={mockSession as any} recipe={mockRecipe} />);
        expect(screen.getByText('Mark Done')).toBeDefined();
    });

    it('triggers go_to_step action', () => {
        (useCookNext as any).mockReturnValue({
            data: {
                actions: [{ type: 'go_to_step', label: 'Next Step', step_idx: 1 }],
                reason: 'Test'
            },
            isLoading: false
        });

        render(<NextUpPanel session={mockSession as any} recipe={mockRecipe} />);
        fireEvent.click(screen.getByTestId('next-action-go_to_step'));
        expect(mockPatch).toHaveBeenCalledWith({
            sessionId: 's1',
            patch: { current_step_index: 1 }
        });
    });
});
