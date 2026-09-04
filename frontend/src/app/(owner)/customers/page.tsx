'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { Customer } from '@/types';
import { Docket, LoadingState, EmptyState, Cash } from '@/components/ui';

export default function CustomersPage() {
  const { businessId, currentBusiness } = useBusiness();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', email: '', phone: '' });

  useEffect(() => {
    if (!businessId) return;
    loadCustomers();
  }, [businessId]);

  const loadCustomers = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/customers/${businessId}`);
      setCustomers(res.data);
    } catch {
      console.error('Failed to load customers.');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!form.name) return alert('Name is required.');
    try {
      await api.post(`/customers/${businessId}`, form);
      setForm({ name: '', email: '', phone: '' });
      setShowForm(false);
      loadCustomers();
      notifyDataChanged();
    } catch {
      alert('Failed to add customer.');
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
        title='Customers'
        memo='client index · the faces behind the orders'
        action={
          <button onClick={() => setShowForm(!showForm)} className='btn btn-primary'>
            {showForm ? '✕ Close form' : '+ New client'}
          </button>
        }
      />

      {showForm && (
        <div className='ledger p-6 sm:p-8'>
          <p className='kicker mb-5'>Client card · new entry</p>
          <div className='grid grid-cols-1 sm:grid-cols-3 gap-x-8 gap-y-6'>
            <div>
              <label className='label mb-1' htmlFor='c-name'>
                Name *
              </label>
              <input id='c-name' className='field' value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder='Customer name' />
            </div>
            <div>
              <label className='label mb-1' htmlFor='c-email'>
                Email
              </label>
              <input id='c-email' className='field' type='email' value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder='email@example.com' />
            </div>
            <div>
              <label className='label mb-1' htmlFor='c-phone'>
                Phone
              </label>
              <input id='c-phone' className='field' value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder='+880…' />
            </div>
          </div>
          <div className='flex gap-3 mt-7'>
            <button onClick={() => setShowForm(false)} className='btn btn-ghost'>
              Cancel
            </button>
            <button onClick={handleAdd} className='btn btn-primary'>
              File card
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <LoadingState label='opening the client index…' />
      ) : customers.length === 0 ? (
        <EmptyState title='No clients on file' note='add your regulars so the support agent knows who they are' />
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-7'>
          {customers.map((customer) => (
            <article key={customer.id} className='ledger p-5'>
              <div className='flex items-start justify-between gap-3'>
                <span
                  aria-hidden
                  className='inline-flex items-center justify-center w-10 h-10 border border-ink font-display text-lg font-bold'
                >
                  {customer.name.charAt(0).toUpperCase() || '?'}
                </span>
                <span className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint'>
                  client no. {customer.id.slice(0, 6).toUpperCase()}
                </span>
              </div>
              <h2 className='font-display text-lg font-bold leading-tight mt-3'>{customer.name}</h2>
              <p className='font-mono text-xs text-ink-soft mt-1 truncate'>{customer.email || 'No email on file'}</p>
              <p className='font-mono text-xs text-ink-soft truncate'>{customer.phone || 'No phone on file'}</p>
              <dl className='mt-4 pt-4 border-t border-[var(--rule)] flex items-baseline justify-between'>
                <dt className='kicker'>Orders · spent</dt>
                <dd className='font-mono text-sm font-semibold tabular'>
                  {customer.total_orders} · <Cash value={customer.total_spent || 0} currency={currentBusiness?.currency} />
                </dd>
              </dl>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}