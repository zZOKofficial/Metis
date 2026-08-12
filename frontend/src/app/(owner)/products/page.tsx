'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { Product } from '@/types';
import { Docket, LoadingState, EmptyState, Cash } from '@/components/ui';

export default function ProductsPage() {
  const { businessId } = useBusiness();
  const [products, setProducts] = useState<Product[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', description: '', price: '', stock: '', category: '' });

  useEffect(() => {
    if (!businessId) return;
    loadProducts();
  }, [businessId]);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/products/${businessId}`);
      setProducts(res.data);
    } catch {
      console.error('Failed to load products.');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!form.name || !form.price) return alert('Name and price are required.');
    try {
      await api.post(`/products/${businessId}`, {
        name: form.name,
        description: form.description,
        price: parseFloat(form.price),
        stock: parseInt(form.stock) || 0,
        category: form.category,
        status: 'active',
        variants: [],
      });
      setForm({ name: '', description: '', price: '', stock: '', category: '' });
      setShowForm(false);
      loadProducts();
      notifyDataChanged();
    } catch {
      alert('Failed to add product.');
    }
  };

  if (!businessId) {
    return (
      <p className='font-mono text-xs uppercase tracking-[0.14em] text-ink-faint mt-10 text-center'>
        Please set up your business first.
      </p>
    );
  }

  return (
    <div className='space-y-8'>
      <Docket
        title='Products'
        memo='shelf register · what the sales agent can promise'
        action={
          <button onClick={() => setShowForm(!showForm)} className='btn btn-primary'>
            {showForm ? '✕ Close form' : '+ New entry'}
          </button>
        }
      />

      {showForm && (
        <div className='ledger p-6 sm:p-8'>
          <p className='kicker mb-5'>Stock entry form · line item</p>
          <div className='grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6'>
            <div>
              <label className='label mb-1' htmlFor='p-name'>
                Name *
              </label>
              <input id='p-name' className='field' value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder='Product name' />
            </div>
            <div>
              <label className='label mb-1' htmlFor='p-category'>
                Category
              </label>
              <input id='p-category' className='field' value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder='e.g., Shirts' />
            </div>
            <div>
              <label className='label mb-1' htmlFor='p-price'>
                Price (৳) *
              </label>
              <input id='p-price' className='field tabular' type='number' value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder='0.00' />
            </div>
            <div>
              <label className='label mb-1' htmlFor='p-stock'>
                Stock on hand
              </label>
              <input id='p-stock' className='field tabular' type='number' value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} placeholder='0' />
            </div>
            <div className='sm:col-span-2'>
              <label className='label mb-1' htmlFor='p-desc'>
                Description
              </label>
              <textarea id='p-desc' className='field' rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder='What is it, and what makes it worth the price?' />
            </div>
          </div>
          <div className='flex gap-3 mt-7'>
            <button onClick={() => setShowForm(false)} className='btn btn-ghost'>
              Cancel
            </button>
            <button onClick={handleAdd} className='btn btn-primary'>
              File entry
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <LoadingState label='counting the shelves…' />
      ) : products.length === 0 ? (
        <EmptyState title='The shelves are empty' note='file your first stock entry to give the sales agent something to sell' />
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-7'>
          {products.map((product) => (
            <article key={product.id} className='ledger p-5 flex flex-col'>
              <header className='flex items-start justify-between gap-3'>
                <h2 className='font-display text-lg font-bold leading-tight'>{product.name}</h2>
                <StockTicket stock={product.stock} />
              </header>
              <p className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint mt-1.5'>
                {product.category || 'uncategorised'}
              </p>
              <p className='text-sm text-ink-soft leading-relaxed mt-3 mb-4 flex-1'>
                {product.description || 'No description on file.'}
              </p>
              <footer className='flex items-baseline justify-between border-t border-[var(--rule)] pt-3 mt-auto'>
                <Cash value={product.price} className='font-mono text-xl font-semibold' />
                <span className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint'>per unit</span>
              </footer>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function StockTicket({ stock }: { stock: number }) {
  const tone = stock > 5 ? 'ticket--ok' : stock > 0 ? 'ticket--warn' : 'ticket--danger';
  const label = stock > 5 ? `${stock} in stock` : stock > 0 ? `low · ${stock} left` : 'out of stock';
  return <span className={`ticket ${tone}`}>{label}</span>;
}