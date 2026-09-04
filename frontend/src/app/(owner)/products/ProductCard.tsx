'use client';

import { useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { Product } from '@/types';
import { Cash } from '@/components/ui';

interface Props {
  product: Product;
  onEdit: (product: Product) => void;
}

export default function ProductCard({ product, onEdit }: Props) {
  const { businessId, currentBusiness } = useBusiness();
  const [qty, setQty] = useState('');
  const [busy, setBusy] = useState<string | null>(null);

  const handleRestock = async () => {
    const amount = parseInt(qty, 10);
    if (!amount || amount <= 0) return alert('Enter a quantity greater than zero.');
    if (busy) return;
    setBusy('restock');
    try {
      await api.put(`/products/${businessId}/${product.id}`, {
        stock: product.stock + amount,
        status: product.status === 'out_of_stock' ? 'active' : product.status,
      });
      setQty('');
      notifyDataChanged();
    } catch {
      alert('Failed to restock. Make sure the backend is running.');
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete "${product.name}" from the catalog? This cannot be undone.`)) return;
    setBusy('delete');
    try {
      await api.delete(`/products/${businessId}/${product.id}`);
      notifyDataChanged();
    } catch {
      alert('Failed to delete product.');
    } finally {
      setBusy(null);
    }
  };

  return (
    <article className='ledger p-5 flex flex-col'>
      <header className='flex items-start justify-between gap-3'>
        <div className='min-w-0'>
          <h2 className='font-display text-lg font-bold leading-tight break-words'>{product.name}</h2>
          <p className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint mt-1.5'>
            {product.category || 'uncategorised'}
          </p>
        </div>
        <StockTicket stock={product.stock} />
      </header>
      {product.product_key && (
        <p className='inline-flex items-center gap-1.5 self-start mt-2 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-soft border border-[var(--rule)] px-2 py-0.5'>
          <span aria-hidden>⌗</span>
          {product.product_key}
        </p>
      )}
      <p className='text-sm text-ink-soft leading-relaxed mt-3 mb-4 flex-1'>
        {product.description || 'No description on file.'}
      </p>
      <form
        className='flex items-center gap-2 border-t border-[var(--rule)] pt-3 mb-3'
        onSubmit={(e) => {
          e.preventDefault();
          handleRestock();
        }}
      >
        <input
          type='number'
          min='1'
          step='1'
          className='field tabular !py-2 !px-3 w-24'
          placeholder='qty'
          value={qty}
          onChange={(e) => setQty(e.target.value)}
          aria-label={`Restock quantity for ${product.name}`}
        />
        <button type='submit' disabled={busy !== null} className='btn btn-ghost flex-1 !py-2 !px-3 text-[11px]'>
          {busy === 'restock' ? 'Restocking…' : '+ Restock'}
        </button>
      </form>
      <div className='flex items-center gap-2 border-t border-[var(--rule)] pt-3 mb-3'>
        <button onClick={() => onEdit(product)} disabled={busy !== null} className='btn btn-ghost flex-1 !py-2 !px-3 text-[11px]'>
          Edit
        </button>
        <button onClick={handleDelete} disabled={busy !== null} className='btn btn-danger-ghost flex-1 !py-2 !px-3 text-[11px]'>
          {busy === 'delete' ? 'Deleting…' : 'Delete'}
        </button>
      </div>
      <footer className='flex items-baseline justify-between border-t border-[var(--rule)] pt-3 mt-auto'>
        <Cash value={product.price} currency={currentBusiness?.currency} className='font-mono text-xl font-semibold' />
        <span className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint'>per unit</span>
      </footer>
    </article>
  );
}

function StockTicket({ stock }: { stock: number }) {
  const tone = stock > 5 ? 'ticket--ok' : stock > 0 ? 'ticket--warn' : 'ticket--danger';
  const label = stock > 5 ? `${stock} in stock` : stock > 0 ? `low · ${stock} left` : 'out of stock';
  return <span className={`ticket ${tone}`}>{label}</span>;
}