'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogIn, Sparkles } from 'lucide-react';
import { authApi, setAuthToken } from '@/lib/api';

const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'ResearchOS';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await authApi.login(email, password);
      setAuthToken(data.access_token);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
    setLoading(false);
  };

  const handleDemoLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await authApi.demoLogin();
      setAuthToken(data.access_token);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Demo login failed');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold text-2xl mx-auto mb-4 shadow-lg">
            R
          </div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">Sign in to {APP_NAME}</h1>
          <p className="text-sm text-surface-500 mt-2">Access research tools and AI-powered analysis</p>
        </div>

        <div className="card p-6 space-y-6">
          {/* Demo Login */}
          <button
            onClick={handleDemoLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gradient-to-r from-brand-600 to-blue-600 text-white font-semibold hover:from-brand-700 hover:to-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50"
          >
            <Sparkles className="w-5 h-5" />
            Quick Demo Login
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-surface-200 dark:border-surface-700" /></div>
            <div className="relative flex justify-center text-sm"><span className="px-3 bg-white dark:bg-surface-800 text-surface-400">or sign in with email</span></div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Email</label>
              <input type="email" className="input" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Password</label>
              <input type="password" className="input" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && <div className="text-sm text-negative font-medium">{error}</div>}
            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
              <LogIn className="w-4 h-4 mr-2" /> Sign In
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-surface-400 mt-6">
          Demo credentials: demo@researchos.dev / demo123456
        </p>
      </div>
    </div>
  );
}
