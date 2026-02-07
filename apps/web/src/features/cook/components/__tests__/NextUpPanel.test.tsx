import { render, screen, fireEvent } from '@testing-library/react';
import { NextUpPanel } from '../NextUpPanel';
import { useCookAutoflow, useCookSessionPatch, useCookTimerAction, useCookTimerCreate, useCookSessionEnd } from '../../hooks';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../hooks', () => ({
    useCookAutoflow: vi.fn(),
    useCookSessionPatch: vi.fn(),
    useCookTimerCreate: vi.fn(),
    useCookTimerAction: vi.fn(),
    useCookSessionEnd: vi.fn()
}));

const mockSession = {
    id: 's1',
    recipe_id: 'r1',
    status: 'active',
    current_step_index: 0,
    state_version: 1,
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
        (useCookAutoflow as any).mockReturnValue({
            data: {
                suggestions: [{ 
                    type: 'complete_step', 
                    label: 'Complete Step', 
                    confidence: 'high',
                    action: {
                        op: 'patch_session',
                        payload: { mark_step_complete: 0 }
                    }
                }],
                source: 'heuristic',
                autoflow_id: 'test-1'
            },
            isLoading: false
        });

        render(<NextUpPanel session={mockSession as any} recipe={mockRecipe} />);
        expect(screen.getByText('Complete Step')).toBeDefined();
    });

    it('triggers create_timer action', () => {
        (useCookAutoflow as any).mockReturnValue({
            data: {
                suggestions: [{ 
                    type: 'start_timer', 
                    label: 'Start 10m Boil',
                    confidence: 'high',
                    action: {
                        op: 'create_timer',
                        payload: { duration_s: 600 }
                    }
                }],
                source: 'heuristic',
                autoflow_id: 'test-2'
            },
            isLoading: false
        });

        render(<NextUpPanel session={mockSession as any} recipe={mockRecipe} />);
        fireEvent.click(screen.getByTestId('autoflow-action-start_timer'));
        expect(mockCreateTimer).toHaveBeenCalledWith(expect.objectContaining({
            sessionId: 's1',
            payload: expect.objectContaining({
                duration_sec: 600,
                label: 'Start 10m Boil'
            })
        }));
    });
});
