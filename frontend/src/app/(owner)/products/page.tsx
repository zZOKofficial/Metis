'use client';

import { useEffect, useMemo, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { useDataRefresh } from '@/lib/refresh';
import { Product } from '@/types';
import { Docket, LoadingState, EmptyState } from '@/components/ui';
import ProductForm from './ProductForm';
import ProductCard from './ProductCard';

export default function ProductsPage() {
  const { businessId } = useBusiness();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [query, setQuery] = useState('');

  const loadProducts = async () => {
    if (!businessId) return;
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

  useEffect(() => {
    if (!businessId) return;
    loadProducts();
  }, [businessId]);

  useDataRefresh(loadProducts);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q) ||
        (p.product_key || '').toLowerCase().includes(q)
    );
  }, [products, query]);

  const closeForm = () => {
    setShowForm(false);
    setEditing(null);
  };

  const startEdit = (product: Product) => {
    setShowForm(false);
    setEditing(product);
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
          <button
            onClick={() => {
              closeForm();
              setShowForm(!showForm);
            }}
            className='btn btn-primary'
          >
            {showForm ? '✕ Close form' : '+ New entry'}
          </button>
        }
      />

      {(showForm || editing) && (
        <ProductForm
          initial={editing}
          onDone={closeForm}
          onCancel={closeForm}
        />
      )}

      {products.length > 0 && (
        <div className='ledger--flat p-4 sm:p-5'>
          <label className='label mb-2' htmlFor='p-search'>
            Search the shelves
          </label>
          <input
            id='p-search'
            className='field'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='By name, category or product key…'
          />
        </div>
      )}

      {loading ? (
        <LoadingState label='counting the shelves…' />
      ) : products.length === 0 ? (
        <EmptyState title='The shelves are empty' note='file your first stock entry to give the sales agent something to sell' />
      ) : filtered.length === 0 ? (
        <EmptyState title='Nothing matches that search' note='try a different name, category or product key' />
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-7'>
          {filtered.map((product) => (
            <ProductCard key={product.id} product={product} onEdit={startEdit} />
          ))}
        </div>
      )}
    </div>
  );
}