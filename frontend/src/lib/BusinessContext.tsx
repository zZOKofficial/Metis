import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Business } from '@/types';
import { businessExists } from '@/lib/api';

interface BusinessContextType {
  currentBusiness: Business | null;
  setCurrentBusiness: (business: Business | null) => void;
  businessId: string;
  setBusinessId: (id: string) => void;
  clearBusiness: () => void;
}

const BusinessContext = createContext<BusinessContextType | undefined>(undefined);

export function BusinessProvider({ children }: { children: ReactNode }) {
  const [currentBusiness, setCurrentBusiness] = useState<Business | null>(null);
  const [businessId, setBusinessId] = useState<string>('');

  useEffect(() => {
    const saved = localStorage.getItem('metis_business');
    if (!saved) return;

    let business: Business;
    try {
      business = JSON.parse(saved);
    } catch {
      localStorage.removeItem('metis_business');
      return;
    }

    setCurrentBusiness(business);
    setBusinessId(business.id);

    // The cached business can outlive the backend it was created against.
    // Drop it if the backend no longer knows it, so the user lands on the
    // Setup Wizard instead of a wall of 404s.
    let cancelled = false;
    businessExists(business.id).then((exists) => {
      if (cancelled || exists) return;
      localStorage.removeItem('metis_business');
      setCurrentBusiness(null);
      setBusinessId('');
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const clearBusiness = () => {
    setCurrentBusiness(null);
    setBusinessId('');
    localStorage.removeItem('metis_business');
  };

  return (
    <BusinessContext.Provider value={{ currentBusiness, setCurrentBusiness, businessId, setBusinessId, clearBusiness }}>
      {children}
    </BusinessContext.Provider>
  );
}

export function useBusiness() {
  const context = useContext(BusinessContext);
  if (!context) throw new Error('useBusiness must be used within BusinessProvider');
  return context;
}
