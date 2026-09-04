'use client';

import { useCallback, useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { useDataRefresh } from '@/lib/refresh';
import { Order } from '@/types';
import { Docket, LoadingState, EmptyState, Cash, DateTime } from '@/components/ui';

const STATUS_TONE: Record<string, string> = {
  pending: 'ticket--warn',
  confirmed: 'ticket--carbon',
  processing: 'ticket--carbon',
  shipped: 'ticket--carbon',
  delivered: 'ticket--ok',
  cancelled: 'ticket--danger',
  returned: 'ticket--danger',
};

export default function OrdersPage() {
  const { businessId, currentBusiness } = useBusiness();
  const [orders, setOrders] = useState<Order[]>([]);
  const [customerNames, setCustomerNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  const loadOrders = useCallback(async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const [ordersRes, customersRes] = await Promise.all([
        api.get(`/orders/${businessId}`),
        api.get(`/customers/${businessId}`),
      ]);
      setOrders(ordersRes.data);
      setCustomerNames(
        Object.fromEntries(customersRes.data.map((c: { id: string; name: string }) => [c.id, c.name]))
      );
    } catch {
      console.error('Failed to load orders.');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  useDataRefresh(loadOrders);

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
        title='Orders'
        memo='sales dockets · from order to delivery'
        action={
          <button onClick={loadOrders} className='btn btn-ghost'>
            ↻ Recheck
          </button>
        }
      />

      {loading ? (
        <LoadingState label='pulling the sales dockets…' />
      ) : orders.length === 0 ? (
        <EmptyState title='No dockets on file yet' note='orders taken by the sales agent will land here' />
      ) : (
        <div className='space-y-7'>
          <p className='font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft'>
            {orders.length} order{orders.length === 1 ? '' : 's'} · newest first
          </p>
          {orders.map((order) => (
            <article key={order.id} className='ledger p-6 sm:p-7'>
              <header className='flex flex-wrap items-start justify-between gap-3'>
                <div>
                  <div className='flex flex-wrap items-center gap-3'>
                    <p className='font-display text-xl font-bold tracking-tight'>
                      Docket #{order.id.slice(0, 8).toUpperCase()}
                    </p>
                    <span className={`ticket ${STATUS_TONE[order.status] || 'ticket--carbon'}`}>{order.status}</span>
                  </div>
                  <p className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft mt-1'>
                    Filed <DateTime value={order.created_at} /> · {order.items?.length || 0} line
                    {(order.items?.length || 0) === 1 ? '' : 's'}
                  </p>
                </div>
                <div className='text-right'>
                  <span className='font-mono text-xs text-ink-faint'>
                    customer #{order.customer_id?.slice(0, 8).toUpperCase() || '—'}
                  </span>
                  {customerNames[order.customer_id] && (
                    <p className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft mt-0.5'>
                      {customerNames[order.customer_id]}
                    </p>
                  )}
                </div>
              </header>

              <table className='w-full mt-5 border-collapse text-sm'>
                <thead>
                  <tr className='border-b border-[var(--rule)]'>
                    <th scope='col' className='kicker py-2 pr-3 text-left'>
                      Item
                    </th>
                    <th scope='col' className='kicker py-2 px-3 text-right hidden sm:table-cell'>
                      Qty
                    </th>
                    <th scope='col' className='kicker py-2 px-3 text-right hidden sm:table-cell'>
                      Unit
                    </th>
                    <th scope='col' className='kicker py-2 pl-3 text-right'>
                      Line total
                    </th>
                  </tr>
                </thead>
                <tbody className='divide-y divide-[var(--rule)]'>
                  {order.items?.map((item, i) => (
                    <tr key={i}>
                      <td className='py-2.5 pr-3'>{item.product_name}</td>
                      <td className='py-2.5 px-3 text-right tabular hidden sm:table-cell'>{item.quantity}</td>
                      <td className='py-2.5 px-3 text-right tabular hidden sm:table-cell'>
                        <Cash value={item.unit_price} currency={currentBusiness?.currency} />
                      </td>
                      <td className='py-2.5 pl-3 text-right tabular font-medium'>
                        <Cash value={item.total_price} currency={currentBusiness?.currency} />
                      </td>
                    </tr>
                  )) || (
                    <tr>
                      <td className='py-2.5 text-ink-soft'>No line items recorded.</td>
                    </tr>
                  )}
                </tbody>
              </table>

              <footer className='dashed-print mt-5 pt-4 flex items-baseline justify-end gap-3'>
                <a
                  href={`/orders/${order.id}/receipt`}
                  target='_blank'
                  rel='noopener noreferrer'
                  className='btn btn-ghost mr-auto text-[12px]'
                >
                  ⤓ Memo
                </a>
                <span className='kicker'>Total payable</span>
                <Cash value={order.total_amount} currency={currentBusiness?.currency} className='font-mono text-2xl font-semibold' />
              </footer>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}