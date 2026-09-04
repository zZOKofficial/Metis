import axios from 'axios';
import { AiConfigStatus } from '@/types';
import { authEnabled } from '@/lib/authConfig';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

/** Storefront endpoints are public -- shoppers have no account to prove. */
function isPublicPath(url = ''): boolean {
  return url.startsWith('/storefront') || url.startsWith('/currencies');
}

/**
 * The caller's ID token, or null.
 *
 * Firebase is imported dynamically so the SDK stays out of the initial bundle
 * of pages that never sign anyone in -- above all the public storefront, which
 * imports this client only to talk to open endpoints.
 */
async function bearerToken(url?: string): Promise<string | null> {
  if (!authEnabled || isPublicPath(url)) return null;
  const { getIdToken } = await import('@/lib/firebase');
  return getIdToken();
}

// Attach the caller's identity to every request. Null when auth is not
// configured or nobody is signed in, in which case the backend treats the
// request as anonymous -- which is what a local install wants.
api.interceptors.request.use(async (config) => {
  const token = await bearerToken(config.url);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** Auth headers for callers that bypass axios (see lib/sse.ts). */
export async function authHeaders(path?: string): Promise<Record<string, string>> {
  const token = await bearerToken(path);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchAiConfig(): Promise<AiConfigStatus> {
  const res = await api.get('/models');
  return {
    models: res.data.models || [],
    default: res.data.default || '',
    configured: !!res.data.configured,
    key_source: res.data.key_source ?? null,
  };
}

export async function saveAiConfig(apiKey: string): Promise<void> {
  await api.post('/ai/config', { api_key: apiKey });
}

export async function clearAiConfig(): Promise<void> {
  await api.post('/ai/config/clear');
}

export interface AiKeyTestResult {
  valid: boolean;
  error: string | null;
}

export async function testAiConfig(apiKey?: string): Promise<AiKeyTestResult> {
  const res = await api.post('/ai/config/test', { api_key: apiKey || '' });
  return { valid: !!res.data.valid, error: res.data.error ?? null };
}

/**
 * The businesses the signed-in caller owns.
 *
 * This is the source of truth for which shop the app opens. The active
 * business is cached in localStorage for a fast first paint, but that cache
 * outlives the database it came from (a reset dev DB, a different backend, a
 * deleted store) and, once accounts exist, can belong to a different user
 * entirely -- so it always has to be reconciled against this.
 *
 * Returns null, distinct from an empty array, when the backend could not be
 * reached: "you own nothing" and "we couldn't ask" must not be confused, or a
 * network blip would throw the owner back into the Setup Wizard.
 */
export async function fetchMyBusinesses(): Promise<any[] | null> {
  try {
    const res = await api.get('/businesses');
    return Array.isArray(res.data) ? res.data : [];
  } catch {
    return null;
  }
}

export default api;