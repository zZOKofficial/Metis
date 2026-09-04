'use client';

import { useState } from 'react';
import type { ChangeEvent } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { Product } from '@/types';

interface DraftValues {
  name?: string;
  description?: string;
  price?: number;
  category?: string;
}

interface Props {
  initial?: Product | null;
  draft?: DraftValues | null;
  onDone: () => void;
  onCancel: () => void;
}

const EMPTY = { name: '', description: '', product_key: '', price: '', stock: '', category: '' };

export default function ProductForm({ initial, draft, onDone, onCancel }: Props) {
  const { businessId } = useBusiness();
  const isEdit = Boolean(initial);
  const [form, setForm] = useState(() => {
    if (initial) {
      return {
        name: initial.name,
        description: initial.description,
        product_key: initial.product_key || '',
        price: String(initial.price),
        stock: String(initial.stock),
        category: initial.category || '',
      };
    }
    if (draft) {
      return {
        ...EMPTY,
        name: draft.name || '',
        description: draft.description || '',
        price: draft.price ? String(draft.price) : '',
        category: draft.category || '',
      };
    }
    return EMPTY;
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (key: keyof typeof EMPTY) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async () => {
    if (!form.name.trim()) return setError('A product name is required.');
    const price = parseFloat(form.price);
    if (isNaN(price) || price < 0) return setError('Enter a valid price (0 or more).');
    const stock = parseInt(form.stock, 10) || 0;
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      description: form.description.trim(),
      product_key: form.product_key.trim(),
      price,
      stock,
      category: form.category.trim(),
      status: stock > 0 && initial?.status === 'out_of_stock' ? 'active' : initial?.status || 'active',
    };
    if (!isEdit) payload.variants = [];

    setSaving(true);
    setError('');
    try {
      if (isEdit && initial) {
        await api.put(`/products/${businessId}/${initial.id}`, payload);
      } else {
        await api.post(`/products/${businessId}`, payload);
      }
      notifyDataChanged();
      onDone();
    } catch (err: any) {
      setError(err?.response?.status === 409 ? 'That product key is already in use.' : isEdit ? 'Failed to save changes.' : 'Failed to add product.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className='ledger p-6 sm:p-8'>
      <p className='kicker mb-5'>{isEdit ? 'Edit entry · line item' : 'Stock entry form · line item'}</p>
      {!isEdit && draft && (
        <p className='font-mono text-[11px] uppercase tracking-[0.12em] text-ink-faint border border-dashed border-[var(--rule)] px-3 py-2 mb-5'>
          Drafted from your photo — review before filing.
        </p>
      )}
      <div className='grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-6'>
        <div>
          <label className='label mb-1' htmlFor='p-name'>
            Name *
          </label>
          <input id='p-name' className='field' value={form.name} onChange={set('name')} placeholder='Product name' />
        </div>
        <div>
          <label className='label mb-1' htmlFor='p-key'>
            Product key
          </label>
          <input id='p-key' className='field font-mono' value={form.product_key} onChange={set('product_key')} placeholder='e.g., SKU-001' />
          <p className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint mt-1.5'>Optional · must be unique if set</p>
        </div>
        <div>
          <label className='label mb-1' htmlFor='p-category'>
            Category
          </label>
          <input id='p-category' className='field' value={form.category} onChange={set('category')} placeholder='e.g., Shirts' />
        </div>
        <div>
          <label className='label mb-1' htmlFor='p-price'>
            Price (৳) *
          </label>
          <input id='p-price' className='field tabular' type='number' min='0' step='any' value={form.price} onChange={set('price')} placeholder='0.00' />
        </div>
        <div>
          <label className='label mb-1' htmlFor='p-stock'>
            Stock on hand
          </label>
          <input id='p-stock' className='field tabular' type='number' min='0' step='1' value={form.stock} onChange={set('stock')} placeholder='0' />
        </div>
        <div className='sm:col-span-2'>
          <label className='label mb-1' htmlFor='p-desc'>
            Description
          </label>
          <textarea id='p-desc' className='field' rows={2} value={form.description} onChange={set('description')} placeholder='What is it, and what makes it worth the price?' />
        </div>
      </div>
      {error && <p className='font-mono text-[11px] uppercase tracking-[0.12em] text-stamp mt-5'>{error}</p>}
      <div className='flex gap-3 mt-7'>
        <button onClick={onCancel} className='btn btn-ghost' disabled={saving}>
          Cancel
        </button>
        <button onClick={handleSubmit} className='btn btn-primary' disabled={saving}>
          {saving ? (isEdit ? 'Saving…' : 'Filing…') : isEdit ? 'Save changes' : 'File entry'}
        </button>
      </div>
    </div>
  );
}