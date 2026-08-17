'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Search, TrendingUp, BarChart3, Bell, BookOpen, Sparkles } from 'lucide-react';
import { companiesApi, concallsApi, announcementsApi, getAuthToken } from '@/lib/api';
import { CompanySearch } from '@/components/company-search';

const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'ResearchOS';

export default function DashboardPage() {
  const isLoggedIn = !!getAuthToken();

  const { data: recentConcalls } = useQuery({
    queryKey: ['concalls', 'recent'],
    queryFn: () => concallsApi.recent(),
    enabled: true,
  });

  const { data: announcements } = useQuery({
    queryKey: ['announcements', 'feed'],
    queryFn: () => announcementsApi.feed(),
    enabled: true,
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl sm:text-5xl font-extrabold bg-gradient-to-r from-brand-600 via-brand-500 to-blue-400 bg-clip-text text-transparent mb-4">
          {APP_NAME}
        </h1>
        <p className="text-lg text-surface-500 dark:text-surface-400 max-w-2xl mx-auto mb-8">
          Indian equity research powered by verified AI. Search companies, analyze financials, and discover opportunities.
        </p>
        <CompanySearch />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {[
          { icon: BarChart3, label: 'Companies', value: '10', color: 'text-brand-500' },
          { icon: TrendingUp, label: 'Sectors', value: '10', color: 'text-positive' },
          { icon: Bell, label: 'Announcements', value: String(announcements?.length || 0), color: 'text-warning' },
          { icon: Sparkles, label: 'AI Summaries', value: 'Available', color: 'text-purple-500' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="card p-4 text-center">
            <Icon className={`w-6 h-6 mx-auto mb-2 ${color}`} />
            <div className="data-value">{value}</div>
            <div className="data-label">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Concalls */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-200 dark:border-surface-700 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900 dark:text-surface-100">Recent Earnings Calls</h2>
            <BookOpen className="w-4 h-4 text-surface-400" />
          </div>
          <div className="divide-y divide-surface-100 dark:divide-surface-800">
            {(recentConcalls || []).slice(0, 5).map((c: any) => (
              <div key={c.id} className="px-5 py-3 hover:bg-surface-50 dark:hover:bg-surface-700/50 transition-colors">
                <div className="text-sm font-medium text-surface-900 dark:text-surface-100 truncate">{c.title}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`badge ${c.has_transcript ? 'badge-positive' : 'badge-warning'}`}>
                    {c.has_transcript ? 'Transcript' : 'Pending'}
                  </span>
                  <span className="text-xs text-surface-400">
                    {c.scheduled_at ? new Date(c.scheduled_at).toLocaleDateString('en-IN') : ''}
                  </span>
                </div>
              </div>
            ))}
            {(!recentConcalls || recentConcalls.length === 0) && (
              <div className="px-5 py-8 text-center text-surface-400 text-sm">No recent concalls</div>
            )}
          </div>
        </div>

        {/* Latest Announcements */}
        <div className="card">
          <div className="px-5 py-4 border-b border-surface-200 dark:border-surface-700 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900 dark:text-surface-100">Latest Announcements</h2>
            <Bell className="w-4 h-4 text-surface-400" />
          </div>
          <div className="divide-y divide-surface-100 dark:divide-surface-800">
            {(announcements || []).slice(0, 5).map((a: any) => (
              <div key={a.id} className="px-5 py-3 hover:bg-surface-50 dark:hover:bg-surface-700/50 transition-colors">
                <div className="text-sm font-medium text-surface-900 dark:text-surface-100 truncate">{a.title}</div>
                <div className="flex items-center gap-2 mt-1">
                  {a.is_material && <span className="badge badge-negative">Material</span>}
                  {a.category_name && <span className="badge badge-info">{a.category_name}</span>}
                  <span className="text-xs text-surface-400">
                    {a.published_at ? new Date(a.published_at).toLocaleDateString('en-IN') : ''}
                  </span>
                </div>
              </div>
            ))}
            {(!announcements || announcements.length === 0) && (
              <div className="px-5 py-8 text-center text-surface-400 text-sm">No announcements</div>
            )}
          </div>
        </div>
      </div>

      {/* Login CTA */}
      {!isLoggedIn && (
        <div className="mt-10 card p-8 text-center bg-gradient-to-br from-brand-50 to-blue-50 dark:from-brand-950/30 dark:to-blue-950/30 border-brand-200 dark:border-brand-800">
          <Sparkles className="w-8 h-8 mx-auto mb-3 text-brand-500" />
          <h3 className="text-lg font-semibold mb-2">Unlock AI Research Features</h3>
          <p className="text-sm text-surface-500 mb-4">Sign in to access watchlists, AI summaries, document chat, and more.</p>
          <Link href="/login" className="btn-primary">
            Demo Login
          </Link>
        </div>
      )}
    </div>
  );
}
