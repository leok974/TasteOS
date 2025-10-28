/**
 * Login page for Phase 1 development
 *
 * Simple token paste interface for testing.
 * Production will use OAuth/proper authentication.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setToken } from '../lib/auth';
import { Button } from '@tasteos/ui';

export function Login() {
  const [token, setTokenInput] = useState('');
  const navigate = useNavigate();

  const handleLogin = () => {
    if (!token.trim()) {
      alert('Please paste a JWT token');
      return;
    }

    setToken(token.trim());
    navigate('/recipes');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center text-gray-900">
            TasteOS Dashboard
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Phase 1 Dev Login
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="token" className="block text-sm font-medium text-gray-700">
              JWT Token
            </label>
            <textarea
              id="token"
              rows={6}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm font-mono"
              placeholder="Paste your JWT token here..."
              value={token}
              onChange={(e) => setTokenInput(e.target.value)}
            />
          </div>

          <Button
            onClick={handleLogin}
            className="w-full"
          >
            Login with Token
          </Button>

          <div className="text-xs text-gray-500 space-y-1">
            <p>To get a token:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Run: <code className="bg-gray-100 px-1">.\apps\api\scripts\login.ps1</code></li>
              <li>Copy the access_token value</li>
              <li>Paste it above</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
