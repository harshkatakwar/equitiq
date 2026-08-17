'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';
import { companiesApi } from '@/lib/api';

export function CompanySearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await companiesApi.search(query, 8);
        setResults(data);
        setShowResults(true);
      } catch (e) { setResults([]); }
      setLoading(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setShowResults(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIndex(i => Math.min(i + 1, results.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIndex(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && selectedIndex >= 0) {
      router.push(`/company/${results[selectedIndex].id}`);
      setShowResults(false);
    }
    if (e.key === 'Escape') setShowResults(false);
  };

  return (
    <div ref={wrapperRef} className="relative max-w-xl mx-auto w-full">
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-400" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search companies by name, symbol, or ISIN..."
          className="w-full pl-12 pr-4 py-3 rounded-xl border-2 border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-base focus:border-brand-500 focus:ring-2 focus:ring-brand-200 dark:focus:ring-brand-800 transition-all shadow-sm hover:shadow-md"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setSelectedIndex(-1); }}
          onFocus={() => results.length > 0 && setShowResults(true)}
          onKeyDown={handleKeyDown}
        />
        {loading && <div className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />}
      </div>

      {showResults && results.length > 0 && (
        <div className="absolute top-full mt-2 w-full bg-white dark:bg-surface-800 rounded-xl border border-surface-200 dark:border-surface-700 shadow-xl overflow-hidden z-50 animate-fade-in">
          {results.map((company, idx) => (
            <button
              key={company.id}
              className={`w-full px-4 py-3 flex items-center justify-between text-left hover:bg-surface-50 dark:hover:bg-surface-700 transition-colors ${
                idx === selectedIndex ? 'bg-brand-50 dark:bg-brand-900/30' : ''
              }`}
              onClick={() => { router.push(`/company/${company.id}`); setShowResults(false); }}
            >
              <div>
                <div className="text-sm font-semibold text-surface-900 dark:text-surface-100">{company.name}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  {company.symbols?.map((s: any) => (
                    <span key={s.id} className="text-xs font-mono text-brand-600 dark:text-brand-400">
                      {s.exchange_code}:{s.symbol}
                    </span>
                  ))}
                  {company.sector && <span className="text-xs text-surface-400">• {company.sector}</span>}
                </div>
              </div>
              {company.latest_price && (
                <div className="text-right">
                  <div className="text-sm font-mono font-semibold text-surface-900 dark:text-surface-100">
                    ₹{Number(company.latest_price).toLocaleString('en-IN')}
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
