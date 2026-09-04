'use client';

import { useBusiness } from '@/lib/BusinessContext';
import { useAuth } from '@/lib/AuthContext';
import { useRouter } from 'next/navigation';

export default function Header({ onMenu }: { onMenu: () => void }) {
  const { currentBusiness, clearBusiness } = useBusiness();
  const { user, enabled, signOut } = useAuth();
  const router = useRouter();

  const handleReset = () => {
    if (confirm('Reset your business? This will clear all local data.')) {
      clearBusiness();
      router.push('/');
    }
  };

  const handleSignOut = async () => {
    // Clear the cached business too: the next person to sign in on this
    // machine must not inherit the last one's shop.
    clearBusiness();
    try {
      await signOut();
    } finally {
      router.replace('/login');
    }
  };

  return (
    <header className='no-print bg-ink text-card border-b border-white/10 lg:h-[52px] h-auto'>
      <div className='flex items-center justify-between gap-3 px-4 sm:px-8 lg:px-12 py-2.5'>
        <div className='flex items-center gap-3 min-w-0'>
          <button
            onClick={onMenu}
            aria-label='Open menu'
            className='lg:hidden font-mono text-sm text-card/70 border border-card/30 px-2 py-1 leading-none'
          >
            ☰
          </button>
          <p className='font-display text-base font-bold truncate'>{currentBusiness?.name || 'METIS'}</p>
          {currentBusiness && (
            <span className='ticket ticket--carbon hidden sm:inline-flex lg:hidden'>{currentBusiness.category}</span>
          )}
        </div>
        <div className='flex items-center gap-4'>
          {currentBusiness && (
            <>
              <span className='hidden md:flex lg:hidden items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-card/50'>
                <span aria-hidden className='inline-block w-1.5 h-1.5 rounded-full bg-ok blink' />
                Workforce on duty
              </span>
              <button
                onClick={handleReset}
                className='font-mono text-[10px] uppercase tracking-[0.14em] text-card/60 border border-card/25 px-2.5 py-1 hover:text-card hover:border-card/60 transition-colors'
              >
                Reset
              </button>
            </>
          )}
          {enabled && user && (
            <>
              <span
                className='hidden lg:inline font-mono text-[10px] uppercase tracking-[0.14em] text-card/45 truncate max-w-[180px]'
                title={user.email || undefined}
              >
                {user.email}
              </span>
              <button
                onClick={handleSignOut}
                className='font-mono text-[10px] uppercase tracking-[0.14em] text-card/60 border border-card/25 px-2.5 py-1 hover:text-card hover:border-card/60 transition-colors'
              >
                Sign out
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}