'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Search, Menu, X, Moon, Sun, User, LogOut } from 'lucide-react';
import { getAuthToken, setAuthToken } from '@/lib/api';
import { CompanySearch } from '@/components/company-search';

const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'ResearchOS';

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const isLoggedIn = typeof window !== 'undefined' ? !!getAuthToken() : false;

  const toggleDark = () => {
    setDark(!dark);
    document.documentElement.classList.toggle('dark');
  };

  const logout = () => {
    setAuthToken(null);
    window.location.href = '/';
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-surface-900/80 backdrop-blur-xl border-b border-surface-200 dark:border-surface-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold text-sm group-hover:shadow-lg transition-shadow">
              R
            </div>
            <span className="font-bold text-lg text-surface-900 dark:text-surface-100 hidden sm:block">{APP_NAME}</span>
          </Link>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-6">
            <Link href="/" className="text-sm font-medium text-surface-600 dark:text-surface-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors">Dashboard</Link>
            {isLoggedIn && (
              <>
                <Link href="/watchlists" className="text-sm font-medium text-surface-600 dark:text-surface-400 hover:text-brand-600 transition-colors">Watchlists</Link>
                <Link href="/subscription" className="text-sm font-medium text-surface-600 dark:text-surface-400 hover:text-brand-600 transition-colors">Subscription</Link>
              </>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button onClick={toggleDark} className="p-2 rounded-lg text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors">
              {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            {isLoggedIn ? (
              <button onClick={logout} className="p-2 rounded-lg text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors" title="Logout">
                <LogOut className="w-4 h-4" />
              </button>
            ) : (
              <Link href="/login" className="btn-primary text-sm py-1.5 px-3">Sign In</Link>
            )}
            <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden p-2 rounded-lg text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800">
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 px-4 py-3 space-y-2">
          <Link href="/" className="block py-2 text-sm font-medium text-surface-700 dark:text-surface-300">Dashboard</Link>
          {isLoggedIn && (
            <>
              <Link href="/watchlists" className="block py-2 text-sm font-medium text-surface-700 dark:text-surface-300">Watchlists</Link>
              <Link href="/subscription" className="block py-2 text-sm font-medium text-surface-700 dark:text-surface-300">Subscription</Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
