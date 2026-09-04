'use client';

import { useCallback, useState } from 'react';
import api from './api';

export type BriefingStatus = 'idle' | 'loading' | 'speaking' | 'unsupported' | 'error';

/** Fetches the Manager Agent's daily summary and reads it aloud via the
 * browser's built-in speech synthesis — no server-side TTS, no new deps. */
export function useVoiceBriefing(businessId: string) {
  const [status, setStatus] = useState<BriefingStatus>('idle');
  const [summary, setSummary] = useState('');

  const stop = useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setStatus('idle');
  }, []);

  const play = useCallback(async () => {
    if (!businessId) return;
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setStatus('unsupported');
      return;
    }
    if (status === 'speaking' || status === 'loading') {
      stop();
      return;
    }
    setStatus('loading');
    try {
      const res = await api.get(`/agents/${businessId}/briefing`);
      const text: string = res.data?.summary || '';
      setSummary(text);
      if (!text) {
        setStatus('idle');
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onend = () => setStatus('idle');
      utterance.onerror = () => setStatus('error');
      setStatus('speaking');
      window.speechSynthesis.speak(utterance);
    } catch {
      setStatus('error');
    }
  }, [businessId, status, stop]);

  return { status, summary, play, stop };
}
