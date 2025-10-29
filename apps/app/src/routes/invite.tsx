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
      console.error('[TasteOS][Invite] error:', e);
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
    <main className="bg-app min-h-screen p-6 md:p-8 flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold text-white">Invite to Household</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Generate a secure code to share with new members
        </p>
      </header>

      <div className="max-w-2xl">
        <div className="rounded-xl bg-surface-card border border-border p-6 flex flex-col gap-4">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Generating...' : 'Generate Invite Code'}
          </button>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm p-3">
              {error}
            </div>
          )}

          {tokenData && (
            <div className="rounded-lg bg-surface-muted border border-border p-4 flex flex-col gap-3">
              <div className="text-xs text-muted-foreground">
                Share this code with the person you want to invite:
              </div>

              <div className="rounded-lg bg-black/40 border border-border p-3 font-mono text-sm text-white break-all">
                {tokenData.token}
              </div>

              <button
                onClick={handleCopy}
                className="rounded-lg bg-surface-card border border-border text-white px-3 py-2 text-xs font-medium hover:bg-surface-muted transition-colors"
              >
                Copy to clipboard
              </button>

              <div className="text-[11px] text-muted-foreground">
                Household ID: {tokenData.household_id}
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
