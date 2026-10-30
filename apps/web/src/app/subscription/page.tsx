'use client';

import { useState, useEffect } from 'react';

import { useQuery } from '@tanstack/react-query';
import { CreditCard, BarChart2, CheckCircle } from 'lucide-react';
import { subscriptionApi, getAuthToken } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function SubscriptionPage() {
  const router = useRouter();

  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
    if (!getAuthToken()) router.push('/login');
  }, [router]);

  if (!mounted || !getAuthToken()) return null;

  const { data: subscription } = useQuery({ queryKey: ['subscription'], queryFn: () => subscriptionApi.current() });
  const { data: usage } = useQuery({ queryKey: ['usage'], queryFn: () => subscriptionApi.usage() });

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-6">Subscription & Usage</h1>

      {/* Current Plan */}
      <div className="card p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <CreditCard className="w-5 h-5 text-brand-500" />
          <h2 className="font-semibold text-lg">Current Plan</h2>
        </div>
        {subscription ? (
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-brand-600">{subscription.plan?.name || 'Free'}</span>
              <span className="badge badge-positive">{subscription.status}</span>
            </div>
            {subscription.current_period_end && (
              <p className="text-sm text-surface-400 mt-1">Current period ends: {new Date(subscription.current_period_end).toLocaleDateString('en-IN')}</p>
            )}
          </div>
        ) : (
          <p className="text-surface-400">No active subscription</p>
        )}
      </div>

      {/* Usage */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <BarChart2 className="w-5 h-5 text-brand-500" />
          <h2 className="font-semibold text-lg">Usage This Month</h2>
        </div>
        <div className="space-y-3">
          {(usage?.items || []).map((item: any) => {
            const pct = item.limit ? Math.min((item.used / item.limit) * 100, 100) : 0;
            const isUnlimited = item.limit === null;
            return (
              <div key={item.feature_key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-surface-700 dark:text-surface-300 font-medium">{item.feature_key.replace(/\./g, ' / ').replace(/_/g, ' ')}</span>
                  <span className="font-mono text-surface-500">
                    {item.used} / {isUnlimited ? '∞' : item.limit}
                  </span>
                </div>
                <div className="h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${pct > 80 ? 'bg-negative' : pct > 50 ? 'bg-warning' : 'bg-brand-500'}`}
                    style={{ width: `${isUnlimited ? 0 : pct}%` }}
                  />
                </div>
              </div>
            );
          })}
          {(!usage?.items || usage.items.length === 0) && <p className="text-surface-400 text-sm">No usage data available</p>}
        </div>
      </div>
    </div>
  );
}
