/** API client with auth token management. */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) localStorage.setItem('ros_token', token);
  else localStorage.removeItem('ros_token');
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== 'undefined') {
    authToken = localStorage.getItem('ros_token');
  }
  return authToken;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail?.message || error.detail || `API Error ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: 'DELETE' }),
};

// ─── Auth API ──────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) => api.post<{ access_token: string; user: any }>('/auth/login', { email, password }),
  demoLogin: () => api.post<{ access_token: string; user: any }>('/auth/demo-login'),
  register: (email: string, password: string, display_name?: string) => api.post<{ access_token: string; user: any }>('/auth/register', { email, password, display_name }),
  me: () => api.get<any>('/auth/me'),
};

// ─── Companies API ─────────────────────────────────────────
export const companiesApi = {
  search: (q: string, limit = 20) => api.get<any[]>(`/companies/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  get: (id: string) => api.get<any>(`/companies/${id}`),
  sectors: () => api.get<string[]>('/companies/sectors'),
};

// ─── Financials API ────────────────────────────────────────
export const financialsApi = {
  get: (companyId: string, periodType = 'quarterly', statementType = 'pnl') =>
    api.get<any>(`/companies/${companyId}/financials?period_type=${periodType}&statement_type=${statementType}`),
};

// ─── Documents API ─────────────────────────────────────────
export const documentsApi = {
  list: (companyId: string) => api.get<any[]>(`/companies/${companyId}/documents`),
};

// ─── Concalls API ──────────────────────────────────────────
export const concallsApi = {
  list: (companyId: string) => api.get<any[]>(`/companies/${companyId}/concalls`),
  get: (id: string) => api.get<any>(`/concalls/${id}`),
  transcript: (id: string) => api.get<any>(`/concalls/${id}/transcript`),
  upcoming: () => api.get<any[]>('/concall-calendar/upcoming'),
  recent: () => api.get<any[]>('/concall-calendar/recent'),
};

// ─── Announcements API ────────────────────────────────────
export const announcementsApi = {
  list: (companyId: string) => api.get<any[]>(`/companies/${companyId}/announcements`),
  feed: () => api.get<any[]>('/announcements'),
};

// ─── Watchlists API ────────────────────────────────────────
export const watchlistsApi = {
  list: () => api.get<any[]>('/watchlists'),
  create: (name: string, description?: string) => api.post<any>('/watchlists', { name, description }),
  update: (id: string, data: any) => api.patch<any>(`/watchlists/${id}`, data),
  delete: (id: string) => api.delete(`/watchlists/${id}`),
  addCompany: (watchlistId: string, companyId: string) => api.post<any>(`/watchlists/${watchlistId}/companies`, { company_id: companyId }),
  removeCompany: (watchlistId: string, companyId: string) => api.delete(`/watchlists/${watchlistId}/companies/${companyId}`),
};

// ─── AI API ────────────────────────────────────────────────
export const aiApi = {
  generateConcallSummary: (concallId: string) => api.post<any>('/ai/concall-summary', { concall_id: concallId }),
  getArtifact: (id: string) => api.get<any>(`/ai/artifacts/${id}`),
  chat: (companyId: string, question: string, conversationId?: string) =>
    api.post<any>('/ai/chat', { company_id: companyId, question, conversation_id: conversationId }),
};

// ─── Subscriptions API ─────────────────────────────────────
export const subscriptionApi = {
  current: () => api.get<any>('/subscription'),
  usage: () => api.get<any>('/subscription/usage'),
};
