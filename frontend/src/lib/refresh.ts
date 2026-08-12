'use client';

import { useEffect, useRef } from 'react';

export const DATA_CHANGED_EVENT = 'metis:data-changed';

export function notifyDataChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(DATA_CHANGED_EVENT));
  }
}

export function useDataRefresh(onRefresh: () => void) {
  const callbackRef = useRef(onRefresh);

  useEffect(() => {
    callbackRef.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    const handler = () => callbackRef.current();
    const onFocus = () => callbackRef.current();
    window.addEventListener(DATA_CHANGED_EVENT, handler);
    window.addEventListener('focus', onFocus);
    return () => {
      window.removeEventListener(DATA_CHANGED_EVENT, handler);
      window.removeEventListener('focus', onFocus);
    };
  }, []);
}
