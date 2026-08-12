'use client';

import { useCallback, useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged, useDataRefresh } from '@/lib/refresh';
import { Approval } from '@/types';
import { Docket, LoadingState, EmptyState, AgentDot, AGENT_LABEL, RiskTicket, Stamp, DateTime } from '@/components/ui';

type Stamped = { id: string; verdict: 'approved' | 'rejected' } | null;

export default function ApprovalsPage() {
  const { businessId } = useBusiness();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [stamped, setStamped] = useState<Stamped>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadApprovals = useCallback(async () => {
    if (!businessId) return;
    setLoading(true);
    try {
      const [pendingRes, approvedRes, rejectedRes] = await Promise.all([
        api.get(`/approvals/${businessId}?status=pending`),
        api.get(`/approvals/${businessId}?status=approved`),
        api.get(`/approvals/${businessId}?status=rejected`),
      ]);
      const seen = new Set<string>();
      const all = [...pendingRes.data, ...approvedRes.data, ...rejectedRes.data].filter((a: Approval) =>
        seen.has(a.id) ? false : (seen.add(a.id), true)
      );
      setApprovals(all);
    } catch {
      console.error('Failed to load approvals.');
    } finally {
      setLoading(false);
    }
  }, [businessId]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  useDataRefresh(loadApprovals);

  const decide = async (id: string, verdict: 'approved' | 'rejected') => {
    setBusy(id);
    try {
      await api.post(`/approvals/${businessId}/${id}/${verdict === 'approved' ? 'approve' : 'reject'}`);
      setStamped({ id, verdict });
      window.setTimeout(() => {
        setStamped(null);
        loadApprovals();
        notifyDataChanged();
      }, 950);
    } catch (err) {
      let message = `Couldn't ${verdict === 'approved' ? 'approve' : 'reject'} this action. Make sure the backend is running.`;
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (detail && typeof detail === 'object') {
        const obj = detail as { message?: unknown; execution?: { error?: string } };
        const executionError = obj.execution?.error;
        message = executionError
          ? `${String(obj.message ?? 'Action failed.')} — ${executionError}`
          : String(obj.message ?? 'Action failed.');
      }
      alert(message);
    } finally {
      setBusy(null);
    }
  };

  if (!businessId) {
    return (
      <p className='font-mono text-xs uppercase tracking-[0.14em] text-ink-faint mt-10 text-center'>
        Please set up your business first.
      </p>
    );
  }

  const pending = approvals.filter((a) => a.status === 'pending');
  const history = approvals.filter((a) => a.status !== 'pending');

  return (
    <div className='space-y-8'>
      <Docket
        title='Approval Center'
        memo='your signature authorizes the action · nothing runs without it'
        action={
          <button onClick={loadApprovals} className='btn btn-ghost'>
            ↻ Recheck
          </button>
        }
      />

      {loading ? (
        <LoadingState label='pulling dockets awaiting your signature…' />
      ) : pending.length === 0 ? (
        <EmptyState title='No dockets on the desk' note='actions awaiting your word will be filed here' />
      ) : (
        <div className='space-y-7'>
          <p className='font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft'>
            {pending.length} docket{pending.length === 1 ? '' : 's'} awaiting your signature
          </p>
          {pending.map((approval) => {
            const isStamped = stamped?.id === approval.id;
            return (
              <article key={approval.id} className={`ledger relative p-6 sm:p-7 ${isStamped ? 'fade-up' : ''}`}>
                <div className='flex flex-wrap items-start justify-between gap-4'>
                  <div className='min-w-0'>
                    <div className='flex flex-wrap items-center gap-3 mb-2'>
                      <h2 className='font-display text-2xl font-bold tracking-tight'>{approval.action}</h2>
                      <RiskTicket level={approval.risk_level} />
                    </div>
                    <div className='flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft'>
                      <span className='flex items-center gap-2'>
                        <AgentDot type={approval.agent_type} className='w-2 h-2' />
                        requested by the {AGENT_LABEL[approval.agent_type] || approval.agent_type} agent
                      </span>
                      <span>·</span>
                      <DateTime value={approval.created_at} date />
                    </div>
                  </div>
                  <span className='font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint'>
                    docket #{approval.id.slice(0, 8).toUpperCase()}
                  </span>
                </div>

                <p className='mt-5 text-[15px] leading-relaxed border border-[var(--rule)] bg-paper/60 px-4 py-3'>
                  {approval.reason}
                </p>

                <div className='mt-6 flex flex-wrap gap-3'>
                  <button
                    onClick={() => decide(approval.id, 'approved')}
                    disabled={busy !== null}
                    className='btn btn-primary flex-1 sm:flex-none'
                  >
                    ✓ Approve & execute
                  </button>
                  <button
                    onClick={() => decide(approval.id, 'rejected')}
                    disabled={busy !== null}
                    className='btn btn-danger-ghost flex-1 sm:flex-none'
                  >
                    ✗ Reject
                  </button>
                </div>

                {isStamped && (
                  <div className='absolute inset-0 flex items-center justify-center pointer-events-none'>
                    <Stamp
                      text={stamped?.verdict === 'approved' ? 'Approved' : 'Rejected'}
                      slam
                      tone={stamped?.verdict === 'approved' ? 'ok' : 'danger'}
                      className='stamp--lone text-3xl sm:text-4xl'
                    />
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {history.length > 0 && (
        <section className='ledger p-5' aria-label='Approval history'>
          <h2 className='kicker mb-1'>The record · recently decided</h2>
          <ul className='divide-y divide-[var(--rule)]'>
            {history.slice(0, 10).map((approval) => (
              <li key={approval.id} className='flex flex-wrap items-center justify-between gap-3 py-3'>
                <div className='flex items-center gap-3 min-w-0'>
                  <Stamp
                    small
                    text={approval.status === 'approved' ? 'Approved' : 'Rejected'}
                    tone={approval.status === 'approved' ? 'ok' : 'danger'}
                    className='stamp--lone shrink-0'
                  />
                  <div className='min-w-0'>
                    <p className='text-sm font-semibold truncate'>{approval.action}</p>
                    <p className='font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint'>
                      {AGENT_LABEL[approval.agent_type] || approval.agent_type} · {approval.risk_level} risk
                    </p>
                  </div>
                </div>
                <DateTime value={approval.created_at} date />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}