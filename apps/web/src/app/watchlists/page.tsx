'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, X, FolderOpen } from 'lucide-react';
import { watchlistsApi, getAuthToken } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function WatchlistsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const queryClient = useQueryClient();
  const router = useRouter();


  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
    if (!getAuthToken()) router.push('/login');
  }, [router]);

  if (!mounted || !getAuthToken()) return null;

  const { data: watchlists, isLoading } = useQuery({
    queryKey: ['watchlists'],
    queryFn: () => watchlistsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => watchlistsApi.create(newName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlists'] });
      setShowCreate(false);
      setNewName('');
    },
    onError: (err: any) => alert(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => watchlistsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlists'] }),
  });

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">Watchlists</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary"><Plus className="w-4 h-4 mr-1" /> New Watchlist</button>
      </div>

      {showCreate && (
        <div className="card p-4 mb-4 flex items-center gap-3 animate-slide-up">
          <input className="input flex-1" placeholder="Watchlist name" value={newName} onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createMutation.mutate()} autoFocus />
          <button onClick={() => createMutation.mutate()} className="btn-primary" disabled={!newName.trim()}>Create</button>
          <button onClick={() => setShowCreate(false)} className="btn-secondary"><X className="w-4 h-4" /></button>
        </div>
      )}

      {isLoading && <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}</div>}

      <div className="space-y-3">
        {(watchlists || []).map((w: any) => (
          <div key={w.id} className="card-hover p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FolderOpen className="w-5 h-5 text-brand-500" />
                <div>
                  <div className="font-semibold text-surface-900 dark:text-surface-100">{w.name}</div>
                  <div className="text-xs text-surface-400">{w.company_count} companies</div>
                </div>
              </div>
              <button onClick={() => deleteMutation.mutate(w.id)} className="p-2 text-surface-400 hover:text-negative transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
        {(!watchlists || watchlists.length === 0) && !isLoading && (
          <div className="text-center py-16">
            <FolderOpen className="w-12 h-12 mx-auto mb-3 text-surface-300" />
            <p className="text-surface-400">No watchlists yet. Create one to start tracking companies.</p>
          </div>
        )}
      </div>
    </div>
  );
}
