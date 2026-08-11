'use client';

import { useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';

export default function SetupWizard() {
  const { setCurrentBusiness, setBusinessId } = useBusiness();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    category: 'Clothing',
    description: '',
    contact_email: '',
    phone: '',
  });

  const handleSubmit = async () => {
    if (!form.name) return alert('Please enter a business name.');
    setLoading(true);

    try {
      const res = await api.post('/business', {
        name: form.name,
        category: form.category,
        description: form.description,
        contact_email: form.contact_email,
        phone: form.phone,
      });

      const business = {
        id: res.data.id,
        name: form.name,
        category: form.category,
        description: form.description,
        contact_email: form.contact_email,
        phone: form.phone,
        operating_hours: '9AM - 9PM',
        policies: { returns: '7 day return policy', shipping: 'Free delivery over ৳2000' },
        goals: ['Increase online sales'],
        created_at: new Date().toISOString(),
      };

      setCurrentBusiness(business);
      setBusinessId(res.data.id);
      localStorage.setItem('metis_business', JSON.stringify(business));
    } catch {
      alert('Failed to create business. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='max-w-2xl mx-auto'>
      <div className='card'>
        <h1 className='text-2xl font-bold text-slate-800 mb-2'>Welcome to METIS</h1>
        <p className='text-slate-500 mb-6'>Set up your business to get started with your AI workforce.</p>

        <div className='flex gap-2 mb-8'>
          {[1, 2, 3].map((s) => (
            <div key={s} className={`h-2 flex-1 rounded-full ${s <= step ? 'bg-metis-500' : 'bg-slate-200'}`} />
          ))}
        </div>

        {step === 1 && (
          <div className='space-y-4'>
            <h2 className='text-lg font-semibold'>Business Information</h2>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Business Name</label>
              <input className='input' value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder='e.g., Fashion Hub BD' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Category</label>
              <select className='input' value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option>Clothing</option>
                <option>Electronics</option>
                <option>Cosmetics</option>
                <option>Food & Beverage</option>
                <option>Home & Living</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Description</label>
              <textarea className='input' rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder='Tell us about your business...' />
            </div>
            <button onClick={() => setStep(2)} className='btn-primary w-full'>Continue</button>
          </div>
        )}

        {step === 2 && (
          <div className='space-y-4'>
            <h2 className='text-lg font-semibold'>Contact Details</h2>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Email</label>
              <input className='input' type='email' value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} placeholder='owner@business.com' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Phone</label>
              <input className='input' value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder='+880 1XXX-XXXXXX' />
            </div>
            <div className='flex gap-3'>
              <button onClick={() => setStep(1)} className='btn-secondary flex-1'>Back</button>
              <button onClick={() => setStep(3)} className='btn-primary flex-1'>Continue</button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className='space-y-4'>
            <h2 className='text-lg font-semibold'>Ready to Launch</h2>
            <div className='bg-slate-50 rounded-lg p-4 space-y-2'>
              <p className='text-sm'><strong>Name:</strong> {form.name}</p>
              <p className='text-sm'><strong>Category:</strong> {form.category}</p>
              <p className='text-sm'><strong>Email:</strong> {form.contact_email || 'Not provided'}</p>
              <p className='text-sm'><strong>Phone:</strong> {form.phone || 'Not provided'}</p>
            </div>
            <div className='bg-metis-50 border border-metis-200 rounded-lg p-4'>
              <p className='text-sm text-metis-700'>Your AI workforce is ready. METIS will deploy 6 specialized agents to operate your business.</p>
            </div>
            <div className='flex gap-3'>
              <button onClick={() => setStep(2)} className='btn-secondary flex-1' disabled={loading}>Back</button>
              <button onClick={handleSubmit} className='btn-primary flex-1' disabled={loading}>
                {loading ? 'Launching...' : 'Launch METIS'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
