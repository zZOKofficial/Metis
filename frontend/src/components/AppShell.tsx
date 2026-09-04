'use client';

import { useState } from 'react';
import { BusinessProvider } from '@/lib/BusinessContext';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [railOpen, setRailOpen] = useState(false);

  return (
    <BusinessProvider>
      <div className='min-h-screen bg-ink lg:flex'>
        <div className='no-print hidden lg:block lg:static fixed inset-y-0 left-0 z-40'>
          <Sidebar />
        </div>

        <div className={`no-print lg:hidden fixed inset-0 z-50 transition-opacity ${railOpen ? 'opacity-100' : 'pointer-events-none opacity-0'}`}>
          <button
            aria-label='Close menu'
            className='absolute inset-0 bg-ink/60'
            onClick={() => setRailOpen(false)}
          />
          <div className={`absolute inset-y-0 left-0 transition-transform duration-200 ${railOpen ? 'translate-x-0' : '-translate-x-full'}`}>
            <Sidebar onNavigate={() => setRailOpen(false)} />
          </div>
        </div>

        <div className='flex-1 flex flex-col min-w-0 lg:h-screen lg:overflow-hidden'>
          <Header onMenu={() => setRailOpen(true)} />
          <main className='desk flex-1 overflow-y-auto px-4 py-6 sm:px-8 lg:px-12 lg:py-8'>{children}</main>
        </div>
      </div>
    </BusinessProvider>
  );
}