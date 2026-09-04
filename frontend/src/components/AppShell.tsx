'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { BusinessProvider } from '@/lib/BusinessContext';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';

/**
 * Keeps the owner pages behind a sign-in.
 *
 * This is the only place the guard lives: `(owner)/layout.tsx` renders nothing
 * but AppShell, so every owner page inherits it, while the public storefront
 * sits outside the (owner) group and is deliberately untouched.
 *
 * When auth is not configured for the deployment (`enabled` false), it steps
 * aside entirely — a local single-user install has nobody to sign in as.
 */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading, enabled } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (enabled && !loading && !user) router.replace('/login');
  }, [enabled, loading, user, router]);

  if (enabled && loading) {
    return (
      <div className='min-h-screen bg-ink flex items-center justify-center px-4'>
        <p className='font-mono text-xs uppercase tracking-[0.16em] text-ink-faint'>
          checking your credentials…
        </p>
      </div>
    );
  }

  // Redirecting; render nothing rather than flashing the desk to a signed-out
  // visitor.
  if (enabled && !user) return null;

  return <>{children}</>;
}

function Desk({ children }: { children: React.ReactNode }) {
  const [railOpen, setRailOpen] = useState(false);

  return (
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
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AuthGate>
        <BusinessProvider>
          <Desk>{children}</Desk>
        </BusinessProvider>
      </AuthGate>
    </AuthProvider>
  );
}
