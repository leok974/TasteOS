/**
 * InviteOwnerPage - Phase 6.2
 * 
 * Allows household owners to generate invite codes for new members.
 */

import { useState } from 'react';

export default function InviteOwnerPage() {
  const [tokenData, setTokenData] = useState<null | {
    token: string;
    household_id: string;
  }>(null);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    setError(null);
    setLoading(true);
    try {
      const base = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
      const res = await fetch(`${base}/api/v1/households/invite`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          invited_email: 'member@example.com',
          role: 'member',
        }),
      });

      if (!res.ok) {
        if (res.status === 403) {
          throw new Error('Only owners can create invitations');
        }
        throw new Error(`Invite failed: ${res.status}`);
      }

      const json = await res.json();
      setTokenData(json);
    } catch (e: any) {
      console.error(e);
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (tokenData?.token) {
      try {
        await navigator.clipboard.writeText(tokenData.token);
        // Could show a toast here
      } catch {
        /* non-blocking */
      }
    }
  }

  return (
    <main className="p-6 max-w-md mx-auto flex flex-col gap-4 bg-background min-h-screen">
      <h1 className="text-xl font-semibold text-foreground">
        Invite someone to your household
      </h1>
      <p className="text-sm text-muted-foreground">
        They'll get access to shared meals, allergies, and nutrition tracking.
      </p>

      {error && (
        <div className="text-xs text-red-400 font-mono bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          {error}
        </div>
      )}

      <button
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg px-4 py-3 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        onClick={handleGenerate}
        disabled={loading}
      >
        {loading ? 'Generating...' : 'Generate invite code'}
      </button>

      {tokenData && (
        <div className="rounded-xl bg-card border border-border p-4 flex flex-col gap-3">
          <div className="text-xs text-muted-foreground">Share this code:</div>
          <code className="text-foreground text-sm font-mono break-all bg-muted p-3 rounded-lg border border-border">
            {tokenData.token}
          </code>
          <div className="text-[11px] text-muted-foreground">
            Household: {tokenData.household_id}
          </div>

          <button
            className="bg-secondary text-secondary-foreground hover:bg-secondary/80 rounded-lg px-3 py-2 text-xs font-medium self-start transition-colors"
            onClick={handleCopy}
          >
            Copy code
          </button>
        </div>
      )}

      <p className="text-[11px] text-muted-foreground leading-relaxed">
        The invite code allows anyone to join your household as a member. 
        Keep it secure and only share with people you trust.
      </p>
    </main>
  );
}
