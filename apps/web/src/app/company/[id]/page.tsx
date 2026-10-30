'use client';

import { useParams } from 'next/navigation';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Building2, TrendingUp, FileText, Phone, Bell, Sparkles, Plus, ExternalLink } from 'lucide-react';
import { companiesApi, financialsApi, documentsApi, concallsApi, announcementsApi, aiApi, watchlistsApi, getAuthToken } from '@/lib/api';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Building2 },
  { id: 'financials', label: 'Financials', icon: TrendingUp },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'concalls', label: 'Concalls', icon: Phone },
  { id: 'announcements', label: 'Announcements', icon: Bell },
  { id: 'ai', label: 'AI Research', icon: Sparkles },
];

export default function CompanyPage() {
  const params = useParams();
  const companyId = params.id as string;
  const [activeTab, setActiveTab] = useState('overview');
  const isLoggedIn = !!getAuthToken();

  const { data: company, isLoading } = useQuery({
    queryKey: ['company', companyId],
    queryFn: () => companiesApi.get(companyId),
  });

  if (isLoading) return <div className="max-w-7xl mx-auto px-4 py-8"><div className="skeleton h-48 rounded-xl mb-6" /><div className="skeleton h-96 rounded-xl" /></div>;

  if (!company) return <div className="max-w-7xl mx-auto px-4 py-16 text-center text-surface-400">Company not found</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Company Header */}
      <div className="card p-6 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">{company.name}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2">
              {company.securities?.map((s: any) => (
                <span key={s.id} className="badge badge-info font-mono">{s.exchange_code}:{s.symbol}</span>
              ))}
              {company.isin && <span className="text-xs font-mono text-surface-400">ISIN: {company.isin}</span>}
            </div>
            <div className="flex items-center gap-3 mt-2 text-sm text-surface-500">
              {company.sector && <span>{company.sector}</span>}
              {company.industry && <span>• {company.industry}</span>}
            </div>
          </div>
          <div className="text-right">
            {company.latest_price && (
              <div className="text-3xl font-bold font-mono text-surface-900 dark:text-surface-100">
                ₹{Number(company.latest_price).toLocaleString('en-IN')}
              </div>
            )}
            {company.market_cap && (
              <div className="text-sm text-surface-500 font-mono">
                MCap: ₹{(Number(company.market_cap) / 1e7).toFixed(0)} Cr
              </div>
            )}
            <div className="badge badge-positive mt-1 text-xs">Demo Data</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1 border-b border-surface-200 dark:border-surface-700">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg whitespace-nowrap transition-all ${
              activeTab === id
                ? 'text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400 -mb-px bg-brand-50/50 dark:bg-brand-900/20'
                : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="animate-fade-in">
        {activeTab === 'overview' && <OverviewTab company={company} />}
        {activeTab === 'financials' && <FinancialsTab companyId={companyId} companyName={company.name} />}
        {activeTab === 'documents' && <DocumentsTab companyId={companyId} />}
        {activeTab === 'concalls' && <ConcallsTab companyId={companyId} />}
        {activeTab === 'announcements' && <AnnouncementsTab companyId={companyId} />}
        {activeTab === 'ai' && <AITab companyId={companyId} companyName={company.name} isLoggedIn={isLoggedIn} />}
      </div>
    </div>
  );
}

function OverviewTab({ company }: { company: any }) {
  return (
    <div className="space-y-6">
      {company.description && (
        <div className="card p-5">
          <h3 className="font-semibold mb-3">About</h3>
          <p className="text-sm text-surface-600 dark:text-surface-400 leading-relaxed">{company.description}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-surface-100 dark:border-surface-800">
            {company.founded_year && <div><div className="data-label">Founded</div><div className="data-value">{company.founded_year}</div></div>}
            {company.headquarters && <div><div className="data-label">HQ</div><div className="data-value text-xs">{company.headquarters}</div></div>}
            {company.sector && <div><div className="data-label">Sector</div><div className="data-value text-xs">{company.sector}</div></div>}
            {company.industry && <div><div className="data-label">Industry</div><div className="data-value text-xs">{company.industry}</div></div>}
          </div>
        </div>
      )}
    </div>
  );
}

function FinancialsTab({ companyId, companyName }: { companyId: string; companyName: string }) {
  const [periodType, setPeriodType] = useState('quarterly');

  const { data, isLoading } = useQuery({
    queryKey: ['financials', companyId, periodType],
    queryFn: () => financialsApi.get(companyId, periodType),
  });

  if (isLoading) return <div className="skeleton h-96 rounded-xl" />;

  const periods = data?.periods || [];
  const allMetrics = Array.from(new Set<string>(periods.flatMap((p: any) => p.metrics?.map((m: any) => m.metric_code) || [])));

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['quarterly', 'annual'].map(pt => (
          <button key={pt} onClick={() => setPeriodType(pt)} className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${periodType === pt ? 'bg-brand-600 text-white' : 'btn-secondary'}`}>
            {pt === 'quarterly' ? 'Quarterly' : 'Annual'}
          </button>
        ))}
      </div>

      <div className="card overflow-x-auto">
        <table className="financial-table w-full">
          <thead>
            <tr>
              <th className="sticky left-0 bg-white dark:bg-surface-800 z-10 min-w-[180px]">Metric (₹ Cr)</th>
              {periods.slice(0, 8).map((p: any, i: number) => (
                <th key={i} className="min-w-[100px]">
                  {p.period_type === 'quarterly' ? `Q${p.fiscal_quarter} FY${p.fiscal_year}` : `FY${p.fiscal_year}`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allMetrics.map((code: string) => {
              const firstName = periods[0]?.metrics?.find((m: any) => m.metric_code === code)?.metric_name || code;
              return (
                <tr key={code} className="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                  <td className="sticky left-0 bg-white dark:bg-surface-800 z-10 text-sm font-medium text-surface-700 dark:text-surface-300">{firstName}</td>
                  {periods.slice(0, 8).map((p: any, i: number) => {
                    const fact = p.metrics?.find((m: any) => m.metric_code === code);
                    return <td key={i} className="text-surface-900 dark:text-surface-100">{fact ? Number(fact.value).toLocaleString('en-IN') : '—'}</td>;
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-surface-400">Demo content — not an exchange filing. Source links available for verified data.</p>
    </div>
  );
}

function DocumentsTab({ companyId }: { companyId: string }) {
  const { data: docs } = useQuery({ queryKey: ['documents', companyId], queryFn: () => documentsApi.list(companyId) });

  return (
    <div className="space-y-3">
      {(docs || []).map((d: any) => (
        <div key={d.id} className="card-hover p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm font-semibold text-surface-900 dark:text-surface-100">{d.title}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="badge badge-info">{d.document_type}</span>
                {d.filing_date && <span className="text-xs text-surface-400">{new Date(d.filing_date).toLocaleDateString('en-IN')}</span>}
              </div>
            </div>
            <FileText className="w-4 h-4 text-surface-400 flex-shrink-0" />
          </div>
        </div>
      ))}
      {(!docs || docs.length === 0) && <div className="text-center py-12 text-surface-400">No documents available</div>}
    </div>
  );
}

function ConcallsTab({ companyId }: { companyId: string }) {
  const { data: concalls } = useQuery({ queryKey: ['concalls', companyId], queryFn: () => concallsApi.list(companyId) });

  return (
    <div className="space-y-3">
      {(concalls || []).map((c: any) => (
        <div key={c.id} className="card-hover p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-sm font-semibold text-surface-900 dark:text-surface-100">{c.title}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`badge ${c.status === 'completed' ? 'badge-positive' : 'badge-warning'}`}>{c.status}</span>
                {c.has_transcript && <span className="badge badge-info">Transcript</span>}
                {c.scheduled_at && <span className="text-xs text-surface-400">{new Date(c.scheduled_at).toLocaleDateString('en-IN')}</span>}
              </div>
            </div>
            <Phone className="w-4 h-4 text-surface-400 flex-shrink-0" />
          </div>
        </div>
      ))}
    </div>
  );
}

function AnnouncementsTab({ companyId }: { companyId: string }) {
  const { data: anns } = useQuery({ queryKey: ['announcements', companyId], queryFn: () => announcementsApi.list(companyId) });

  return (
    <div className="space-y-3">
      {(anns || []).map((a: any) => (
        <div key={a.id} className="card-hover p-4">
          <div className="text-sm font-semibold text-surface-900 dark:text-surface-100">{a.title}</div>
          <div className="flex items-center gap-2 mt-1">
            {a.is_material && <span className="badge badge-negative">Material</span>}
            {a.category_name && <span className="badge badge-info">{a.category_name}</span>}
            {a.published_at && <span className="text-xs text-surface-400">{new Date(a.published_at).toLocaleDateString('en-IN')}</span>}
          </div>
          {a.summary && <p className="text-xs text-surface-500 mt-2 line-clamp-2">{a.summary}</p>}
        </div>
      ))}
    </div>
  );
}

function AITab({ companyId, companyName, isLoggedIn }: { companyId: string; companyName: string; isLoggedIn: boolean }) {
  const [chatQuestion, setChatQuestion] = useState('');
  const [chatResponse, setChatResponse] = useState<any>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState<any>(null);

  const { data: concalls } = useQuery({
    queryKey: ['concalls', companyId],
    queryFn: () => concallsApi.list(companyId),
  });

  const handleGenerateSummary = async () => {
    const completedConcall = concalls?.find((c: any) => c.status === 'completed' && c.has_transcript);
    if (!completedConcall) return;
    setSummaryLoading(true);
    try {
      const result = await aiApi.generateConcallSummary(completedConcall.id);
      setSummaryResult(result);
    } catch (err: any) {
      alert(err.message);
    }
    setSummaryLoading(false);
  };

  const handleChat = async () => {
    if (!chatQuestion.trim()) return;
    setChatLoading(true);
    try {
      const result = await aiApi.chat(companyId, chatQuestion);
      setChatResponse(result);
    } catch (err: any) {
      alert(err.message);
    }
    setChatLoading(false);
  };

  if (!isLoggedIn) {
    return (
      <div className="card p-8 text-center">
        <Sparkles className="w-10 h-10 mx-auto mb-3 text-brand-500" />
        <h3 className="text-lg font-semibold mb-2">Sign in for AI Research</h3>
        <p className="text-sm text-surface-500">Generate concall summaries, ask cited questions, and more.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Concall Summary Generator */}
      <div className="card p-5">
        <h3 className="font-semibold mb-3 flex items-center gap-2"><Sparkles className="w-4 h-4 text-brand-500" /> Concall Summary</h3>
        <button onClick={handleGenerateSummary} disabled={summaryLoading} className="btn-primary">
          {summaryLoading ? 'Generating...' : 'Generate Latest Concall Summary'}
        </button>

        {summaryResult && (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className={`badge ${summaryResult.status === 'published' ? 'badge-positive' : 'badge-negative'}`}>
                {summaryResult.status}
              </span>
              <span className="text-xs text-surface-400">
                Claims: {summaryResult.total_claim_count} ({summaryResult.unsupported_claim_count} unsupported)
              </span>
              <span className="text-xs text-surface-400">Model: {summaryResult.model_name}</span>
            </div>
            {summaryResult.content?.sections?.map((s: any, i: number) => (
              <div key={i} className="p-3 bg-surface-50 dark:bg-surface-900 rounded-lg">
                <h4 className="font-medium text-sm text-surface-900 dark:text-surface-100 mb-1">{s.title}</h4>
                <p className="text-xs text-surface-600 dark:text-surface-400">{s.content}</p>
                <div className="mt-1"><span className="text-xs font-medium text-purple-600 dark:text-purple-400">AI Interpretation</span></div>
              </div>
            ))}
            {summaryResult.claims?.length > 0 && (
              <div className="p-3 border border-brand-200 dark:border-brand-800 rounded-lg">
                <h4 className="text-xs font-semibold text-brand-700 dark:text-brand-400 mb-2">Verified Citations</h4>
                {summaryResult.claims.map((c: any, i: number) => (
                  <div key={i} className="text-xs py-1 border-b border-surface-100 dark:border-surface-800 last:border-0">
                    <span className={`inline-block w-2 h-2 rounded-full mr-1 ${c.verification_status === 'verified' ? 'bg-positive' : 'bg-warning'}`} />
                    {c.claim_text}
                    <span className="text-surface-400 ml-1">({c.verification_status})</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Document Chat */}
      <div className="card p-5">
        <h3 className="font-semibold mb-3">Document Chat</h3>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder={`Ask about ${companyName}...`}
            value={chatQuestion}
            onChange={(e) => setChatQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleChat()}
          />
          <button onClick={handleChat} disabled={chatLoading} className="btn-primary">
            {chatLoading ? '...' : 'Ask'}
          </button>
        </div>
        {chatResponse && (
          <div className="mt-4 p-4 bg-surface-50 dark:bg-surface-900 rounded-lg">
            <p className="text-sm text-surface-800 dark:text-surface-200">{chatResponse.answer}</p>
            {chatResponse.citations?.length > 0 && (
              <div className="mt-2 pt-2 border-t border-surface-200 dark:border-surface-700">
                <div className="text-xs font-semibold text-surface-500 mb-1">Sources</div>
                {chatResponse.citations.map((c: any, i: number) => (
                  <div key={i} className="text-xs text-surface-400 py-0.5">
                    [{i+1}] {c.source_type} — {c.text?.substring(0, 80)}...
                  </div>
                ))}
              </div>
            )}
            <div className="mt-2"><span className="text-xs font-medium text-purple-600 dark:text-purple-400">AI Interpretation</span></div>
          </div>
        )}
      </div>
    </div>
  );
}
