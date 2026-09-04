'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useBusiness } from '@/lib/BusinessContext';

const navItems = [
  { href: '/', label: 'Dashboard', glyph: '▤' },
  { href: '/agents', label: 'Agent Center', glyph: '✦' },
  { href: '/chat', label: 'Business Chat', glyph: '✉' },
  { href: '/approvals', label: 'Approvals', glyph: '◉' },
  { href: '/activity', label: 'Activity', glyph: '∿' },
  { href: '/products', label: 'Products', glyph: '☐' },
  { href: '/orders', label: 'Orders', glyph: '∴' },
  { href: '/customers', label: 'Customers', glyph: '◈' },
];

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { currentBusiness } = useBusiness();

  return (
    <aside className='w-64 bg-ink text-card flex flex-col h-full'>
      <div className='px-6 pt-6 pb-5 border-b border-white/10'>
        <p className='font-display text-[26px] font-extrabold leading-none tracking-tight'>METIS</p>
        <p className='font-mono text-[10px] uppercase tracking-[0.24em] text-card/45 mt-2'>
          Μῆτις · your business, operated by AI
        </p>
      </div>

      {currentBusiness && (
        <div className='px-6 py-4 border-b border-white/10'>
          <p className='font-display text-sm font-semibold truncate'>{currentBusiness.name}</p>
          <p className='font-mono text-[10px] uppercase tracking-[0.14em] text-card/40 mt-0.5 truncate'>
            {currentBusiness.category} · est. register no.
          </p>
        </div>
      )}

      <nav className='flex-1 py-4 overflow-y-auto'>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`rail-item flex items-center gap-3 px-6 py-2.5 ${isActive ? 'rail-item--active shadow-print' : ''}`}
            >
              <span aria-hidden className='text-[13px] leading-none w-4 text-center'>
                {item.glyph}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className='px-6 py-4 border-t border-white/10'>
        <div className='flex items-center gap-2'>
          <span aria-hidden className='inline-block w-1.5 h-1.5 rounded-full bg-ok blink' />
          <p className='font-mono text-[10px] uppercase tracking-[0.18em] text-card/45'>Workforce on duty</p>
        </div>
        <p className='font-mono text-[10px] text-card/30 mt-2'>6 specialists · v0.6.2</p>
      </div>
    </aside>
  );
}