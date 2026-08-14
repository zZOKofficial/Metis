'use client';

import { useCallback, useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged, useDataRefresh } from '@/lib/refresh';
import { DashboardMetrics, AgentStatus } from '@/types';
import SetupWizard from '@/components/SetupWizard';
import { Docket, LoadingState, AgentDot, AGENT_LABEL, Cash } from '@/components/ui';

export default function DashboardPage() {
  const { businessId, currentBusiness } = useBusiness();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [restockQty, setRestockQty] = useState<Record<string, string>>({});
  const [restocking, setRestocking] = useState<string | null>(null);

  const handleRestock = async (product: { id: string; name: string; stock: number; status?: string }) => {
    const qty = parseInt(restockQty[product.id] || '', 10);
    if (!qty || qty <= 0) return alert('Enter a quantity greater than zero.');
    if (restocking) return;
    setRestocking(product.id);
    try {
      await api.put(`/products/${businessId}/${product.id}`, {
        stock: product.stock + qty,
        status: product.status === 'out_of_stock' ? 'active' : product.status,
      });
      setRestockQty((prev) => ({ ...prev, [product.id]: '' }));
      notifyDataChanged();
      loadData();
    } catch {
      alert('Failed to restock. Make sure the backend is running.');
    } finally {
      setRestocking(null);
    }
  };

  const loadData = useCallback(async () => {
    if (!businessId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [metricsRes, agentsRes] = await Promise.all([
        api.get(`/analytics/${businessId}/dashboard`),
        api.get(`/agents/${businessId}`),
      ]);
      setMetrics(metricsRes.data);
      setAgents(agentsRes.data);
    } catch (e) {
      console.error('Failed to load dashboard:', e);
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useDataRefresh(loadData);

  if (!businessId) {
    return <SetupWizard />;
  }

  const lowStock = metrics?.low_stock_products || [];

  return (
    <div className='space-y-8'>
      <Docket
        title={currentBusiness?.name || 'Daily register'}
        memo='business overview · work of the day'
        action={
          <div className='flex items-center gap-2 flex-wrap'>
            <a
              href={`/storefront/${businessId}`}
              target='_blank'
              rel='noopener noreferrer'
              className='btn btn-ghost'
            >
              Storefront ↗
            </a>
            <button onClick={loadData} className='btn btn-ghost'>
              ↻ Recheck
            </button>
          </div>
        }
      />

      {loading ? (
        <LoadingState label='pulling the day’s records…' />
      ) : (
        <>
          <section className='ledger overflow-hidden' aria-label='Headline figures'>
            <p className='kicker px-5 pt-4'>Register · total to date</p>
            <div className='grid grid-cols-2 lg:grid-cols-4 divide-x divide-[var(--rule)] border-t border-[var(--rule)]'>
              <RegisterFigure label='Revenue' value={<Cash value={metrics?.total_revenue || 0} />} />
              <RegisterFigure label='Orders' value={String(metrics?.total_orders || 0)} />
              <RegisterFigure label='Customers' value={String(metrics?.total_customers || 0)} />
              <RegisterFigure label='Conversion' value={`${metrics?.conversion_rate || 0}%`} />
            </div>
            {metrics && metrics.average_order_value > 0 && (
              <p className='px-5 pb-4 pt-3 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft'>
                Avg. order value · <Cash value={metrics.average_order_value} className='text-ink' />
                &nbsp;&nbsp;·&nbsp;&nbsp;{metrics.total_orders} order{metrics.total_orders === 1 ? '' : 's'} on the books
              </p>
            )}
          </section>

          <div className='grid grid-cols-1 lg:grid-cols-2 gap-8'>
            <section className='ledger p-5' aria-label='Agents on duty'>
              <div className='flex items-baseline justify-between mb-1'>
                <h2 className='kicker'>Staff roster · agents on duty</h2>
                <span className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint'>
                  {agents.length} of 6
                </span>
              </div>
              <ul className='divide-y divide-[var(--rule)]'>
                {agents.length === 0 && (
                  <li className='py-4 font-mono text-xs uppercase tracking-[0.1em] text-ink-faint'>
                    Roster empty — agents are clocking in.
                  </li>
                )}
                {agents.map((agent) => (
                  <li key={agent.type} className='flex items-center justify-between gap-3 py-3'>
                    <div className='flex items-center gap-3 min-w-0'>
                      <AgentDot type={agent.type} />
                      <span className='font-display text-[15px] font-semibold truncate'>
                        {AGENT_LABEL[agent.type] || agent.name} Agent
                      </span>
                    </div>
                    <div className='flex items-center gap-3'>
                      <span className='font-mono text-xs tabular text-ink-soft hidden sm:inline'>
                        {agent.tasks_completed} tasks
                      </span>
                      <span className='ticket ticket--ok'>active</span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <section className='ledger p-5' aria-label='Manager memo'>
              <h2 className='kicker mb-1'>From the manager’s desk</h2>
              <div className='mt-4 space-y-3'>
                {(metrics?.recommendations?.length ?? 0) === 0 ? (
                  <p className='font-mono text-xs uppercase tracking-[0.1em] text-ink-faint'>
                    No instructions yet. Ask the Manager in Business Chat.
                  </p>
                ) : (
                  metrics!.recommendations.map((rec, i) => (
                    <p key={i} className='text-[15px] leading-relaxed text-ink pl-4 border-l-2 border-carbon'>
                      {rec}
                    </p>
                  ))
                )}
              </div>

              {(metrics?.top_products?.length ?? 0) > 0 && (
                <div className='mt-6'>
                  <p className='kicker mb-1'>Top sellers</p>
                  <ul className='divide-y divide-[var(--rule)]'>
                    {metrics!.top_products.slice(0, 4).map((p, i) => (
                      <li key={p.product_id || i} className='flex items-baseline justify-between gap-3 py-2'>
                        <span className='font-mono text-xs tabular text-ink-soft w-5'>
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <span className='flex-1 text-sm truncate'>{p.name}</span>
                        <span className='font-mono text-xs tabular text-ink-soft'>{p.units_sold} units</span>
                        <Cash value={p.revenue} className='font-mono text-sm font-semibold w-24 text-right' />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          </div>

          {lowStock.length > 0 && (
            <section className='ledger p-5' aria-label='Low stock alerts'>
              <h2 className='kicker mb-3'>
                Stockroom warning · operations agent is watching
              </h2>
              <div className='flex flex-wrap gap-3 items-center'>
                {lowStock.map((p) => (
                  <form
                    key={p.id}
                    className='flex items-center gap-2 ticket ticket--danger !border-dashed !bg-card'
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleRestock(p);
                    }}
                  >
                    <span className='whitespace-nowrap'>
                      {p.name} · {p.stock} left
                    </span>
                    <input
                      type='number'
                      min='1'
                      className='field tabular !py-1 !px-2 w-16'
                      placeholder='qty'
                      value={restockQty[p.id] || ''}
                      onChange={(e) => setRestockQty((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      aria-label={`Restock quantity for ${p.name}`}
                    />
                    <button
                      type='submit'
                      disabled={restocking !== null}
                      className='btn btn-ghost !py-1 !px-2 text-[10px]'
                    >
                      {restocking === p.id ? '…' : '+ Restock'}
                    </button>
                  </form>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function RegisterFigure({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className='px-5 py-5'>
      <p className='kicker'>{label}</p>
      <p className='font-mono text-3xl sm:text-[34px] font-semibold tabular mt-2 leading-none'>{value}</p>
    </div>
  );
}