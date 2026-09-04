'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Business } from '@/types';
import { fetchMyBusinesses } from '@/lib/api';

const CACHE_KEY = 'metis_business';

interface BusinessContextType {
  currentBusiness: Business | null;
  setCurrentBusiness: (business: Business | null) => void;
  businessId: string;
  setBusinessId: (id: string) => void;
  clearBusiness: () => void;
  /** False until the backend has told us what this account actually owns. */
  ready: boolean;
}

const BusinessContext = createContext<BusinessContextType | undefined>(undefined);

export function BusinessProvider({ children }: { children: ReactNode }) {
  const [currentBusiness, setCurrentBusiness] = useState<Business | null>(null);
  const [businessId, setBusinessId] = useState<string>('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Paint from cache immediately so the desk doesn't flash empty, then
    // reconcile with the backend. The cache is a convenience, never the
    // authority: it survives a database reset and, now that accounts exist,
    // could belong to a different user than the one signed in.
    let cached: Business | null = null;
    try {
      const saved = localStorage.getItem(CACHE_KEY);
      if (saved) cached = JSON.parse(saved);
    } catch {
      localStorage.removeItem(CACHE_KEY);
    }

    if (cached) {
      setCurrentBusiness(cached);
      setBusinessId(cached.id);
    }

    let cancelled = false;
    fetchMyBusinesses().then((owned) => {
      if (cancelled) return;

      // Backend unreachable: keep whatever we restored and let the pages
      // surface the error, rather than wrongly concluding the user owns
      // nothing and dropping them into the Setup Wizard.
      if (owned === null) {
        setReady(true);
        return;
      }

      const match = cached ? owned.find((b) => b.id === cached!.id) : undefined;
      const next = match || owned[0] || null;

      if (next) {
        setCurrentBusiness(next);
        setBusinessId(next.id);
        localStorage.setItem(CACHE_KEY, JSON.stringify(next));
      } else {
        setCurrentBusiness(null);
        setBusinessId('');
        localStorage.removeItem(CACHE_KEY);
      }
      setReady(true);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const clearBusiness = () => {
    setCurrentBusiness(null);
    setBusinessId('');
    localStorage.removeItem(CACHE_KEY);
  };

  return (
    <BusinessContext.Provider
      value={{ currentBusiness, setCurrentBusiness, businessId, setBusinessId, clearBusiness, ready }}
    >
      {children}
    </BusinessContext.Provider>
  );
}

export function useBusiness() {
  const context = useContext(BusinessContext);
  if (!context) throw new Error('useBusiness must be used within BusinessProvider');
  return context;
}
