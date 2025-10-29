/**
 * Login Page - Phase 6 Auth
 *
 * Email/password login with cookie-based sessions.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const base = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

      const res = await fetch(`${base}/api/v1/auth/login`, {
        method: 'POST',
        credentials: 'include', // IMPORTANT: enables cookies
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      if (!res.ok) {
        setLoading(false);
        if (res.status === 401) {
          setError('Invalid email or password.');
        } else {
          setError('Login failed. Please try again.');
        }
        return;
      }

      // Success -> redirect to dashboard
      navigate('/dashboard');
    } catch (err: any) {
      console.error(err);
      setLoading(false);
      setError('Network error. Please try again.');
    }
  }

  return (
    <main className="bg-app min-h-screen flex items-center justify-center p-6 md:p-8">
      <div className="rounded-2xl bg-surface-card border border-border shadow-sm p-6 w-full max-w-sm flex flex-col gap-4">
        <div className="text-center flex flex-col gap-1">
          <h1 className="text-white text-lg font-semibold">TasteOS Login</h1>
          <p className="text-[12px] text-muted-foreground">Sign in to continue</p>
        </div>

        <form className="flex flex-col gap-4" onSubmit={handleLogin}>
          <label className="flex flex-col gap-2 text-sm">
            <span className="text-muted-foreground">Email</span>
            <input
              className="rounded-lg bg-surface-muted border border-border text-white p-3 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>

          <label className="flex flex-col gap-2 text-sm">
            <span className="text-muted-foreground">Password</span>
            <input
              className="rounded-lg bg-surface-muted border border-border text-white p-3 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {error && (
            <div className="text-[12px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
              {error}
            </div>
          )}

          <button
            className="w-full rounded-lg bg-emerald-600 text-white text-sm font-medium px-4 py-2 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            type="submit"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="text-[11px] text-muted-foreground text-center leading-relaxed">
          Don't have an account?
          <br />
          Contact your administrator to get registered.
        </div>
      </div>
    </main>
  );
}
