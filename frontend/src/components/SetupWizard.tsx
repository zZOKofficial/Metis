'use client';

import { useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { Stamp } from '@/components/ui';

const STEPS = ['Business', 'Contact', 'Verify & launch'] as const;

export default function SetupWizard() {
  const { setCurrentBusiness, setBusinessId } = useBusiness();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    category: 'Clothing',
    description: '',
    contact_email: '',
    phone: '',
  });

  const canContinue = step === 0 ? form.name.trim().length > 0 : true;

  const handleDemo = async () => {
    setLoading(true);
    try {
      const res = await api.post('/demo/seed');
      const business = res.data.business;
      business.id = res.data.business_id;
      setCurrentBusiness(business);
      setBusinessId(business.id);
      localStorage.setItem('metis_business', JSON.stringify(business));
    } catch {
      alert('Failed to load the demo store. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!form.name) {
      alert('Please enter a business name.');
      return;
    }
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
    <div className='max-w-2xl mx-auto mt-4 sm:mt-10'>
      <div className='ledger p-6 sm:p-10'>
        <p className='kicker mb-1.5'>Form no. 01 · new registration</p>
        <h1 className='font-display text-3xl font-bold tracking-tight'>Open the shop’s books</h1>
        <p className='text-ink-soft text-[15px] mt-2 leading-relaxed'>
          Register your business once. METIS then deploys six specialists — manager, sales, support,
          marketing, operations, analytics — and puts them on the payroll.
        </p>

        <button
          onClick={handleDemo}
          disabled={loading}
          className='btn btn-ghost w-full mt-5'
        >
          {loading ? 'Seeding the shelves…' : '⚡ Skip the paperwork — load the demo store'}
        </button>

        <ol className='flex items-center gap-2 mt-8 mb-8' aria-label='Progress'>
          {STEPS.map((label, i) => (
            <li key={label} className='flex-1'>
              <div className={`h-1.5 ${i <= step ? 'bg-ink' : 'bg-ink/15'}`} />
              <p className={`font-mono text-[10px] uppercase tracking-[0.14em] mt-2 ${i <= step ? 'text-ink' : 'text-ink-faint'}`}>
                {String(i + 1).padStart(2, '0')} · {label}
              </p>
            </li>
          ))}
        </ol>

        {step === 0 && (
          <div className='space-y-6'>
            <div>
              <label className='label mb-1' htmlFor='wiz-name'>
                Business name *
              </label>
              <input
                id='wiz-name'
                className='field'
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder='e.g., Fashion Hub BD'
              />
            </div>
            <div>
              <label className='label mb-1' htmlFor='wiz-category'>
                Category
              </label>
              <select
                id='wiz-category'
                className='field'
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                <option>Clothing</option>
                <option>Electronics</option>
                <option>Cosmetics</option>
                <option>Food &amp; Beverage</option>
                <option>Home &amp; Living</option>
                <option>Other</option>
              </select>
            </div>
            <div>
              <label className='label mb-1' htmlFor='wiz-desc'>
                Description
              </label>
              <textarea
                id='wiz-desc'
                className='field'
                rows={3}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder='What do you sell, and to whom? The staff will read this.'
              />
            </div>
            <div className='flex justify-end pt-2'>
              <button onClick={() => setStep(1)} disabled={!canContinue} className='btn btn-primary'>
                Continue →
              </button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className='space-y-6'>
            <div>
              <label className='label mb-1' htmlFor='wiz-email'>
                Email
              </label>
              <input
                id='wiz-email'
                className='field'
                type='email'
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
                placeholder='owner@business.com'
              />
            </div>
            <div>
              <label className='label mb-1' htmlFor='wiz-phone'>
                Phone
              </label>
              <input
                id='wiz-phone'
                className='field'
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder='+880 1XXX-XXXXXX'
              />
            </div>
            <div className='flex gap-3 pt-2'>
              <button onClick={() => setStep(0)} className='btn btn-ghost flex-1 sm:flex-none'>
                ← Back
              </button>
              <button onClick={() => setStep(2)} className='btn btn-primary flex-1 sm:flex-none'>
                Continue →
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className='space-y-6'>
            <div className='ledger--flat p-5'>
              <p className='kicker mb-3'>Registration summary</p>
              <dl className='space-y-2 font-mono text-[13px]'>
                <div className='flex justify-between gap-4'>
                  <dt className='text-ink-soft uppercase text-[10px] tracking-[0.14em] pt-0.5'>Name</dt>
                  <dd className='text-right'>{form.name || '—'}</dd>
                </div>
                <div className='flex justify-between gap-4'>
                  <dt className='text-ink-soft uppercase text-[10px] tracking-[0.14em] pt-0.5'>Category</dt>
                  <dd className='text-right'>{form.category}</dd>
                </div>
                <div className='flex justify-between gap-4'>
                  <dt className='text-ink-soft uppercase text-[10px] tracking-[0.14em] pt-0.5'>Email</dt>
                  <dd className='text-right'>{form.contact_email || 'Not provided'}</dd>
                </div>
                <div className='flex justify-between gap-4'>
                  <dt className='text-ink-soft uppercase text-[10px] tracking-[0.14em] pt-0.5'>Phone</dt>
                  <dd className='text-right'>{form.phone || 'Not provided'}</dd>
                </div>
              </dl>
            </div>

            <div className='border border-carbon px-5 py-4 flex items-start gap-4'>
              <span aria-hidden className='font-display text-2xl leading-none text-carbon mt-0.5'>Μ</span>
              <p className='text-sm text-ink leading-relaxed'>
                On your word, six specialists clock in: Manager coordinates, Sales talks to customers,
                Support keeps policy straight, Marketing drafts your next campaign, Operations watches
                every order and the stockroom, Analytics reads the numbers.
              </p>
            </div>

            <div className='flex gap-3 pt-2'>
              <button onClick={() => setStep(1)} className='btn btn-ghost flex-1 sm:flex-none' disabled={loading}>
                ← Back
              </button>
              <button onClick={handleSubmit} className='btn btn-primary flex-1 sm:flex-none' disabled={loading}>
                {loading ? 'Posting registration…' : 'Stamp & launch'}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className='hidden sm:flex justify-between items-start mt-6 opacity-70'>
        <Stamp text='Received' tone='danger' small />
        <p className='font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint'>
          Company affairs division · open 24h, no holidays
        </p>
      </div>
    </div>
  );
}