'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { Business, Customer, Order } from '@/types';
import { Cash, LoadingState } from '@/components/ui';

const STATUS_TONE: Record<string, string> = {
  pending: 'ticket--warn',
  confirmed: 'ticket--carbon',
  processing: 'ticket--carbon',
  shipped: 'ticket--carbon',
  delivered: 'ticket--ok',
  cancelled: 'ticket--danger',
  returned: 'ticket--danger',
};

const docket = (id?: string | null) => (id ? id.slice(0, 8).toUpperCase() : '—');

/** Date and time as separate lines — at A4 width a single stamp wraps badly. */
function stamped(value?: string | null): [string, string] {
  if (!value) return ['—', ''];
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return [value, ''];
  return [
    d.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' }),
    d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  ];
}

/** A caption/value pair — the memo's unit of record. */
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className='kicker'>{label}</p>
      <p className='font-mono text-[12px] text-ink mt-1 break-words'>{children}</p>
    </div>
  );
}

export default function OrderReceiptPage() {
  const params = useParams<{ orderId: string }>();
  const router = useRouter();
  const orderId = params.orderId;
  const { businessId } = useBusiness();
  const [order, setOrder] = useState<Order | null>(null);
  const [business, setBusiness] = useState<Business | null>(null);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(true);
  const [issued, setIssued] = useState('');

  const load = useCallback(async () => {
    if (!businessId || !orderId) return;
    setLoading(true);
    try {
      // The customer id only exists once the order is in hand, so it is a
      // second hop rather than a third leg of the parallel fetch.
      const [orderRes, businessRes] = await Promise.all([
        api.get(`/orders/${businessId}/${orderId}`),
        api.get(`/business/${businessId}`),
      ]);
      setOrder(orderRes.data);
      setBusiness(businessRes.data);

      const customerId = orderRes.data?.customer_id;
      const customerRes = customerId
        ? await api.get(`/customers/${businessId}/${customerId}`).catch(() => null)
        : null;
      setCustomer(customerRes?.data ?? null);
    } catch {
      console.error('Failed to load order memo.');
    } finally {
      setLoading(false);
    }
  }, [businessId, orderId]);

  useEffect(() => {
    load();
  }, [load]);

  // Client-side only: a server-rendered timestamp would mismatch on hydration.
  useEffect(() => {
    setIssued(new Date().toLocaleString());
  }, []);

  // The orders list opens the memo with target='_blank', so this tab usually has
  // no history of its own and history.back() would be a no-op. Fall back to the
  // orders desk, which is where "back" means to go from here.
  const goBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/orders');
    }
  };

  if (loading) {
    return (
      <div className='max-w-3xl mx-auto mt-10'>
        <LoadingState label='fetching the memo…' />
      </div>
    );
  }

  if (!order) {
    return (
      <div className='max-w-3xl mx-auto mt-10 ledger p-8'>
        <p className='font-display text-xl font-semibold text-ink'>Order not found.</p>
      </div>
    );
  }

  const items = order.items ?? [];
  const lineCount = items.length;
  const subtotal = items.reduce((sum, item) => sum + (item.total_price || 0), 0);
  // Any gap between the lines and the booked total (a discount, a delivery fee)
  // is shown rather than silently absorbed into the payable figure.
  const adjustment = order.total_amount - subtotal;
  const hasAdjustment = Math.abs(adjustment) >= 1;
  const [filedDate, filedTime] = stamped(order.created_at);
  const policies = Object.entries(business?.policies ?? {});
  const contact = [business?.contact_email, business?.phone, business?.operating_hours].filter(Boolean);
  const currency = business?.currency;

  return (
    <div className='sheet max-w-3xl mx-auto mt-4 sm:mt-8'>
      <article className='ledger p-6 sm:p-9'>
        {/* Masthead — whose desk this came from, and what the sheet is. */}
        <header className='avoid-break flex items-start justify-between gap-6 flex-wrap'>
          <div className='min-w-0'>
            <h1 className='font-display text-2xl sm:text-[32px] font-bold tracking-tight leading-tight text-ink'>
              {business?.name || 'This business'}
            </h1>
            <p className='kicker mt-1.5'>{business?.category || 'general store'}</p>
            {contact.length > 0 && (
              <p className='font-mono text-[11px] text-ink-soft mt-2.5 leading-relaxed'>{contact.join(' · ')}</p>
            )}
          </div>
          <div className='text-right shrink-0'>
            <p className='font-display text-lg font-bold tracking-[0.18em] uppercase text-ink'>Order memo</p>
            <p className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft mt-1'>
              docket #{docket(order.id)}
            </p>
            <span className={`ticket ${STATUS_TONE[order.status] || 'ticket--carbon'} mt-2.5`}>{order.status}</span>
          </div>
        </header>

        <div className='dashed-print mt-6' />

        {/* The two parties and the particulars of the sale. */}
        <section className='avoid-break grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-5 mt-6'>
          <div>
            <p className='kicker'>Billed to</p>
            <p className='font-display text-base font-semibold text-ink mt-1'>
              {customer?.name || 'Walk-in customer'}
            </p>
            <p className='font-mono text-[11px] text-ink-soft mt-1 leading-relaxed break-words'>
              customer #{docket(order.customer_id)}
              {customer?.phone ? <><br />{customer.phone}</> : null}
              {customer?.email ? <><br />{customer.email}</> : null}
            </p>
          </div>
          <Field label='Filed'>
            {filedDate}
            <br />
            {filedTime}
          </Field>
          <Field label='Lines · Currency'>
            {lineCount} line{lineCount === 1 ? '' : 's'}
            <br />
            {currency || 'BDT'}
          </Field>
        </section>

        {/* The lines. thead repeats on every page the table spills onto. */}
        <table className='w-full mt-7 border-collapse text-sm'>
          <thead>
            <tr className='border-y border-ink'>
              <th scope='col' className='kicker py-2 pr-3 text-left w-8'>#</th>
              <th scope='col' className='kicker py-2 pr-3 text-left'>Item</th>
              <th scope='col' className='kicker py-2 px-3 text-right'>Qty</th>
              <th scope='col' className='kicker py-2 px-3 text-right'>Unit</th>
              <th scope='col' className='kicker py-2 pl-3 text-right'>Line total</th>
            </tr>
          </thead>
          <tbody className='divide-y divide-[var(--rule)]'>
            {items.length > 0 ? (
              items.map((item, i) => (
                <tr key={`${item.product_id}-${i}`}>
                  <td className='py-2.5 pr-3 font-mono text-[11px] text-ink-faint tabular align-top'>
                    {String(i + 1).padStart(2, '0')}
                  </td>
                  <td className='py-2.5 pr-3 align-top'>{item.product_name}</td>
                  <td className='py-2.5 px-3 text-right tabular align-top'>{item.quantity}</td>
                  <td className='py-2.5 px-3 text-right tabular align-top'>
                    <Cash value={item.unit_price} currency={currency} />
                  </td>
                  <td className='py-2.5 pl-3 text-right tabular font-medium align-top'>
                    <Cash value={item.total_price} currency={currency} />
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className='py-3 font-mono text-[12px] text-ink-soft'>
                  No line items recorded.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Reckoning. The payable bar spans the full measure so a short order
            does not leave a dead block of paper beside a floated column. */}
        <section className='avoid-break mt-4'>
          {hasAdjustment && (
            <dl className='flex justify-end'>
              <div className='w-full sm:w-[280px]'>
                <div className='flex items-baseline justify-between gap-4 py-1'>
                  <dt className='kicker'>Subtotal</dt>
                  <dd className='font-mono text-sm text-ink-soft'>
                    <Cash value={subtotal} currency={currency} />
                  </dd>
                </div>
                <div className='flex items-baseline justify-between gap-4 py-1'>
                  <dt className='kicker'>Adjustment</dt>
                  <dd className='font-mono text-sm text-ink-soft'>
                    {adjustment > 0 ? '+' : '−'}
                    <Cash value={Math.abs(adjustment)} currency={currency} />
                  </dd>
                </div>
              </div>
            </dl>
          )}
          <div className='flex items-baseline justify-between gap-6 border-t-2 border-ink pt-3 mt-2'>
            <p className='kicker text-ink'>
              Total payable · {lineCount} line{lineCount === 1 ? '' : 's'}
            </p>
            <Cash
              value={order.total_amount}
              currency={currency}
              className='font-mono text-2xl font-semibold text-ink'
            />
          </div>
        </section>

        {order.notes && (
          <section className='avoid-break mt-7 pt-4 rule-t'>
            <p className='kicker mb-1.5'>Notes on file</p>
            <p className='text-sm text-ink leading-relaxed whitespace-pre-line'>{order.notes}</p>
          </section>
        )}

        {/* Two ruled lines: the memo is meant to be signed on paper. */}
        <section className='avoid-break grid grid-cols-2 gap-8 mt-14'>
          <div>
            <div className='border-t border-ink pt-1.5' />
            <p className='kicker'>Issued by · {business?.name || 'the house'}</p>
          </div>
          <div>
            <div className='border-t border-ink pt-1.5' />
            <p className='kicker'>Received by · customer</p>
          </div>
        </section>
      </article>

      {policies.length > 0 && (
        <aside className='avoid-break ledger--flat p-5 mt-4'>
          <p className='kicker mb-2.5'>House policies</p>
          <dl className='space-y-1.5 text-[12px]'>
            {policies.map(([key, value]) => (
              <div key={key} className='flex justify-between gap-6'>
                <dt className='kicker pt-0.5 shrink-0'>{key.replace(/_/g, ' ')}</dt>
                <dd className='text-right text-ink font-mono'>{value}</dd>
              </div>
            ))}
          </dl>
        </aside>
      )}

      <p className='font-mono text-[10px] uppercase tracking-[0.18em] text-ink-faint mt-6 text-center leading-relaxed'>
        Μῆτις · think. act. grow. · v0.7.6 · an OxyOrb product
        <br />
        Memo #{docket(order.id)} · issued {issued || '—'}
      </p>

      <div className='no-print mt-6 mb-10 flex justify-center gap-3'>
        <button onClick={() => window.print()} className='btn btn-primary'>
          ⤓ Print / Save as PDF
        </button>
        <button onClick={goBack} className='btn btn-ghost'>
          ← Back to orders
        </button>
      </div>
    </div>
  );
}
