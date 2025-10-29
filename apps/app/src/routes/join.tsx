/**
 * JoinHouseholdPage - Phase 6.2
 *
 * Allows users to join a household using an invite code.
 */

import { useState } from 'react';

export default function JoinHouseholdPage() {
  const [token, setToken] = useState('');
  const [result, setResult] = useState<null | {
    status: string;
    household_id: string;
    role: string;
  }>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleJoin() {
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const base = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
      const res = await fetch(`${base}/api/v1/households/join`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });

      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('Invalid or expired invite code');
        }
        if (res.status === 410) {
          throw new Error('This invite code has already been used');
        }
        if (res.status === 403) {
          throw new Error('This invite has been revoked');
        }
        throw new Error(`Join failed: ${res.status}`);
      }

      const json = await res.json();
      setResult(json);
      // Phase 6.3: will redirect to /dashboard?household=<joined>
    } catch (e: any) {
      console.error(e);
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="bg-app min-h-screen p-6 max-w-md mx-auto flex flex-col gap-4">
      <h1 className="text-xl font-semibold text-white">Join a household</h1>

      <label className="flex flex-col gap-2 text-sm">
        <span className="text-muted-foreground">Invite code</span>
        <input
          className="rounded-lg bg-surface-card border border-border text-white p-3 text-sm font-mono placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="paste-your-code-here"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
      </label>

      {error && (
        <div className="text-xs text-red-400 font-mono bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      <button
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg px-4 py-3 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={handleJoin}
        disabled={loading || !token.trim()}
      >
        {loading ? 'Joining...' : 'Join household'}
      </button>

      <p className="text-[11px] text-muted-foreground leading-relaxed">
        When you join, you'll share nutrition insights and preferences with the household owner.
      </p>

      {result && (
        <div className="rounded-xl bg-surface-card border border-border p-4 flex flex-col gap-3 animate-fade-in">
          <div className="text-white text-base font-semibold">✓ Joined successfully!</div>
          <div className="text-sm text-muted-foreground space-y-1">
            <div>Household: {result.household_id}</div>
            <div>Role: {result.role}</div>
            <div>Status: {result.status}</div>
          </div>
          <div className="text-xs text-muted-foreground mt-2 p-3 bg-surface-muted rounded-lg border border-border">
            You now appear on that household's dashboard. Navigate to the Dashboard to see your
            household.
          </div>
        </div>
      )}
    </main>
  );
}
