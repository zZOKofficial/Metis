'use client';

import { useCallback, useRef, useState } from 'react';

/**
 * Batches rapid `push()` calls (e.g. SSE deltas arriving word-by-word) into
 * throttled state updates, so a chat bubble doesn't re-render on every token.
 */
export function useStreamBatcher(intervalMs = 40) {
  const [text, setText] = useState('');
  const committedRef = useRef('');
  const pendingRef = useRef('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (pendingRef.current) {
      committedRef.current += pendingRef.current;
      pendingRef.current = '';
      setText(committedRef.current);
    }
    timerRef.current = null;
  }, []);

  const push = useCallback(
    (chunk: string) => {
      pendingRef.current += chunk;
      if (!timerRef.current) {
        timerRef.current = setTimeout(flush, intervalMs);
      }
    },
    [flush, intervalMs]
  );

  const reset = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    committedRef.current = '';
    pendingRef.current = '';
    setText('');
  }, []);

  const finish = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    flush();
  }, [flush]);

  return { text, push, reset, finish };
}
