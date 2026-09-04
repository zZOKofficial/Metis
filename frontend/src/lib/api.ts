import axios from 'axios';
import { AiConfigStatus } from '@/types';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

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

export default api;