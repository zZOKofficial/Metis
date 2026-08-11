'use client';

import { BusinessProvider } from '@/lib/BusinessContext';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <BusinessProvider>
      <div className='flex h-screen overflow-hidden'>
        <Sidebar />
        <div className='flex-1 flex flex-col overflow-hidden'>
          <Header />
          <main className='flex-1 overflow-y-auto p-6 bg-slate-50'>
            {children}
          </main>
        </div>
      </div>
    </BusinessProvider>
  );
}
