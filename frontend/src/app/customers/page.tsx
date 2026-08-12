'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { Customer } from '@/types';

export default function CustomersPage() {
  const { businessId } = useBusiness();
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

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>Customers</h1>
        <button onClick={() => setShowForm(!showForm)} className='btn-primary'>+ Add Customer</button>
      </div>

      {showForm && (
        <div className='card'>
          <h3 className='font-semibold mb-4'>New Customer</h3>
          <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Name</label>
              <input className='input' value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder='Customer name' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Email</label>
              <input className='input' type='email' value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder='email@example.com' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Phone</label>
              <input className='input' value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder='+880...' />
            </div>
          </div>
          <div className='flex gap-3 mt-4'>
            <button onClick={() => setShowForm(false)} className='btn-secondary'>Cancel</button>
            <button onClick={handleAdd} className='btn-primary'>Save</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className='card text-center py-12'><p className='text-slate-400'>Loading customers...</p></div>
      ) : customers.length === 0 ? (
        <div className='card text-center py-12'><p className='text-slate-400'>No customers yet.</p></div>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {customers.map((customer) => (
            <div key={customer.id} className='card'>
              <h3 className='font-semibold text-slate-800'>{customer.name}</h3>
              <p className='text-sm text-slate-500'>{customer.email || 'No email'}</p>
              <p className='text-sm text-slate-500'>{customer.phone || 'No phone'}</p>
              <div className='mt-3 pt-3 border-t border-slate-100 flex items-center justify-between'>
                <span className='text-xs text-slate-400'>{customer.total_orders} orders</span>
                <span className='text-sm font-medium text-metis-600'>৳{customer.total_spent?.toLocaleString() || 0}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
