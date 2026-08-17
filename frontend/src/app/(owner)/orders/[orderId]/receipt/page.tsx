'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { Order } from '@/types';
import { Cash, DateTime, LoadingState } from '@/components/ui';

const STATUS_TONE: Record<string, string> = {
  pending: 'ticket--warn',
  confirmed: 'ticket--carbon',
  processing: 'ticket--carbon',
  shipped: 'ticket--carbon',
  delivered: 'ticket--ok',
  cancelled: 'ticket--danger',
  returned: 'ticket--danger',
};

export default function OrderReceiptPage() {
  const params = useParams<{ orderId: string }>();
  const orderId = params.orderId;
  const { businessId } = useBusiness();
  const [order, setOrder] = useState<Order | null>(null);
  const [business, setBusiness] = useState<Record<string, any> | null>(null);
  const [customer, setCustomer] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!businessId || !orderId) return;
    setLoading(true);
    try {
      const [orderRes, businessRes, customerRes] = await Promise.all([
        api.get(`/orders/${businessId}/${orderId}`),
        api.get(`/business/${businessId}`),
        api.get(`/customers/${businessId}/${order?.customer_id}`).catch(() => null),
      ]);
      setOrder(orderRes.data);
      setBusiness(businessRes.data);
      setCustomer(customerRes?.data ?? null);
    } catch {
      console.error('Failed to load order memo.');
    } finally {
      setLoading(false);
    }
  }, [businessId, orderId, order?.customer_id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className='max-w-2xl mx-auto mt-10'>
        <LoadingState label='fetching the memo…' />
      </div>
    );
  }

  if (!order) {
    return (
      <div className='max-w-2xl mx-auto mt-10 ledger p-8'>
        <p className='font-display text-xl font-semibold text-ink'>Order not found.</p>
      </div>
    );
  }

  const policies: [string, string][] = Object.entries((business?.policies as Record<string, string>) || {});

  return (
    <div className='max-w-2xl mx-auto mt-4 sm:mt-8 print:mt-0'>
      <div className='hidden print:block text-center mb-8'>
        <p className='font-mono text-[10px] uppercase tracking-[0.24em] text-ink-faint'>
          METIS · official memo · generated {new Date().toLocaleString()}
        </p>
      </div>

      <div className='ledger p-6 sm:p-10 print:p-0 print:border-0 print:shadow-none'>
        <header className='flex items-start justify-between gap-4 flex-wrap'>
          <div>
            <p className='kicker mb-1'>Order memo · {business?.category || 'general store'}</p>
            <h1 className='font-display text-2xl sm:text-3xl font-bold tracking-tight'>{business?.name || 'This business'}</h1>
          </div>
          <div className='text-right'>
            <span className={`ticket ${STATUS_TONE[order.status] || 'ticket--carbon'}`}>{order.status}</span>
            <p className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft mt-1.5'>
              docket #{order.id.slice(0, 8).toUpperCase()}
            </p>
          </div>
        </header>

        <div className='mt-6 space-y-1 font-mono text-[12px] text-ink-soft'>
          <p>
            Filed <DateTime value={order.created_at} /> · {order.items?.length || 0} line
            {(order.items?.length || 0) === 1 ? '' : 's'}
          </p>
          {customer && (
            <p>
              Customer {customer.name} · customer #{order.customer_id?.slice(0, 8).toUpperCase() || '—'}
              {customer.phone ? ` · ${customer.phone}` : ''}
              {customer.email ? ` · ${customer.email}` : ''}
            </p>
          )}
        </div>

        <table className='w-full mt-6 border-collapse text-sm'>
          <thead>
            <tr className='border-b border-[var(--rule)]'>
              <th scope='col' className='kicker py-2 pr-3 text-left'>Item</th>
              <th scope='col' className='kicker py-2 px-3 text-right'>Qty</th>
              <th scope='col' className='kicker py-2 px-3 text-right'>Unit</th>
              <th scope='col' className='kicker py-2 pl-3 text-right'>Line total</th>
            </tr>
          </thead>
          <tbody className='divide-y divide-[var(--rule)]'>
            {order.items?.map((item, i) => (
              <tr key={i} className='print:break-inside-avoid'>
                <td className='py-2.5 pr-3'>{item.product_name}</td>
                <td className='py-2.5 px-3 text-right tabular'>{item.quantity}</td>
                <td className='py-2.5 px-3 text-right tabular'><Cash value={item.unit_price} /></td>
                <td className='py-2.5 pl-3 text-right tabular font-medium'><Cash value={item.total_price} /></td>
              </tr>
            )) || (
              <tr>
                <td className='py-2.5 text-ink-soft'>No line items recorded.</td>
              </tr>
            )}
          </tbody>
        </table>

        <footer className='dashed-print mt-6 pt-4 flex items-baseline justify-end gap-3'>
          <span className='kicker'>Total payable</span>
          <Cash value={order.total_amount} className='font-mono text-2xl font-semibold' />
        </footer>
      </div>

      {policies.length > 0 && (
        <div className='ledger--flat p-5 mt-4 print:mt-6'>
          <p className='kicker mb-2'>House policies</p>
          <dl className='space-y-1 font-mono text-[12px]'>
            {policies.map(([key, value]) => (
              <div key={key} className='flex justify-between gap-4'>
                <dt className='text-ink-soft uppercase text-[10px] tracking-[0.14em] pt-0.5'>{key}</dt>
                <dd className='text-right text-ink'>{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <p className='font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint mt-6 text-center print:mt-4'>
        Μῆτις · your business, operated by AI · v0.5.0
      </p>

      <div className='mt-6 mb-10 flex justify-center gap-3 print:hidden'>
        <button onClick={() => window.print()} className='btn btn-primary'>
          ⤓ Print / Save as PDF
        </button>
        <button onClick={() => window.history.back()} className='btn btn-ghost'>
          ← Back
        </button>
      </div>
    </div>
  );
}