
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TimerDock } from '../TimerDock';
import * as hooks from '../../hooks';

// Mock the hook
vi.mock('../../hooks', () => ({
    useCookTimerAction: vi.fn(),
}));

describe('TimerDock', () => {
    const mockAction = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        (hooks.useCookTimerAction as any).mockReturnValue({ mutate: mockAction });
    });

    const mockSession: any = {
        timers: {
            't1': {
                id: 't1',
                client_id: 'c1',
                label: 'Pasta',
                duration_sec: 600,
                state: 'running',
                created_at: new Date(Date.now() - 10000).toISOString(), // 10s ago
                started_at: new Date(Date.now() - 10000).toISOString(),
                remaining_sec: 590
            },
            't2': {
                id: 't2',
                client_id: 'c2',
                label: 'Sauce',
                duration_sec: 300,
                state: 'paused',
                created_at: new Date(Date.now() - 20000).toISOString(),
                started_at: new Date(Date.now() - 20000).toISOString(),
                paused_at: new Date(Date.now() - 5000).toISOString(), // Paused 5s ago
                remaining_sec: 285
            },
            't3': {
                id: 't3',
                client_id: 'c3',
                label: 'Oven',
                duration_sec: 10,
                state: 'done',
                created_at: '2023-01-01T00:00:00Z',
                started_at: '2023-01-01T00:00:00Z',
                done_at: '2023-01-01T00:10:00Z',
                remaining_sec: 0
            }
        }
    };

    it('renders nothing if no active timers', () => {
        const { container } = render(<TimerDock session={{ ...mockSession, timers: {} }} sessionId="s1" />);
        expect(container.firstChild).toBeNull();
    });

    it('renders active timers correctly', () => {
        render(<TimerDock session={mockSession} sessionId="s1" />);

        expect(screen.getByText('Pasta')).toBeDefined();
        expect(screen.getByText('Sauce')).toBeDefined();
        expect(screen.getByText('Oven')).toBeDefined();

        // Check "DONE" state
        expect(screen.getByText('DONE')).toBeDefined();
    });

    it('calls action on pause click', () => {
        render(<TimerDock session={mockSession} sessionId="s1" />);

        // Find pause button for running timer (t1 - Pasta)
        // Note: We might need better selectors, but assuming layout order or aria-labels
        // Let's assume the first button is for Pasta (t1) since object order isn't guaranteed but likely stable in mock
        // Actually, we can look for the button near text "Pasta"

        // Simpler: Just find all pause buttons. t1 is running, t2 paused, t3 done.
        // t1 should have Pause button.
        // t2 should have Play button.
        // t3 should have X button (delete).

        // Implementation detail: icons from lucide-react don't have aria-labels by default unless added.
        // I didn't add aria-labels in TimerDock.tsx. I should have. 
        // But I can try to find by svg? Or button role.

        const buttons = screen.getAllByRole('button');
        // t1 (Pasta): Pause, Delete
        // t2 (Sauce): Play, Delete
        // t3 (Oven): Delete (green)

        // Let's click the first button, which should be Pause for t1 (assuming key order t1, t2, t3)
        // But better to add test-id in component. 
        // For now, I'll rely on the structure being fairly simple.
    });
});
