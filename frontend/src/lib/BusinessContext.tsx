import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Business } from '@/types';

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
    if (saved) {
      try {
        const business = JSON.parse(saved);
        setCurrentBusiness(business);
        setBusinessId(business.id);
      } catch {
        localStorage.removeItem('metis_business');
      }
    }
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
