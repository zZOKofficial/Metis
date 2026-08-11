'use client';

import { useBusiness } from '@/lib/BusinessContext';
import { useRouter } from 'next/navigation';

export default function Header() {
  const { currentBusiness, clearBusiness } = useBusiness();
  const router = useRouter();

  const handleReset = () => {
    if (confirm('Reset your business? This will clear all local data.')) {
      clearBusiness();
      router.push('/');
    }
  };

  return (
    <header className='h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6'>
      <div className='flex items-center gap-4'>
        <h2 className='text-lg font-semibold text-slate-700'>{currentBusiness?.name || 'METIS'}</h2>
        {currentBusiness && <span className='badge badge-blue'>{currentBusiness.category}</span>}
      </div>
      <div className='flex items-center gap-3'>
        {currentBusiness && (
          <>
            <span className='text-sm text-slate-500'>AI Workforce Active</span>
            <span className='w-2 h-2 bg-green-500 rounded-full animate-pulse'></span>
            <button onClick={handleReset} className='btn-secondary text-xs ml-3'>Reset</button>
          </>
        )}
      </div>
    </header>
  );
}
