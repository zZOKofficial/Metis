'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { AgentLog } from '@/types';
import { Docket, LoadingState, EmptyState, AgentDot, AGENT_LABEL, StatusTicket, DateTime } from '@/components/ui';

export default function ActivityPage() {
  const { businessId } = useBusiness();
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!businessId) return;
    loadActivity();
  }, [businessId]);

  const loadActivity = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/agents/${businessId}/activity?limit=100`);
      setLogs(res.data);
    } catch {
      console.error('Failed to load activity.');
    } finally {
      setLoading(false);
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
        title='Activity Feed'
        memo='the day’s ledger · every action, on the record'
        action={
          <button onClick={loadActivity} className='btn btn-ghost'>
            ↻ Recheck
          </button>
        }
      />

      {loading ? (
        <LoadingState label='transcribing the ledger…' />
      ) : logs.length === 0 ? (
        <EmptyState title='The ledger is blank' note='agent actions will be entered here, with time and agent' />
      ) : (
        <div className='ledger overflow-x-auto'>
          <table className='w-full text-left border-collapse'>
            <thead>
              <tr className='border-b-2 border-ink'>
                <th scope='col' className='kicker px-5 py-3 w-16'>
                  Time
                </th>
                <th scope='col' className='kicker px-3 py-3 w-40'>
                  Agent
                </th>
                <th scope='col' className='kicker px-3 py-3'>
                  Action
                </th>
                <th scope='col' className='kicker px-3 py-3 hidden sm:table-cell'>
                  Result
                </th>
                <th scope='col' className='kicker px-5 py-3 w-32 text-right'>
                  Status
                </th>
              </tr>
            </thead>
            <tbody className='divide-y divide-[var(--rule)]'>
              {logs.map((log) => (
                <tr key={log.id} className='hover:bg-paper/70 transition-colors'>
                  <td className='px-5 py-3 font-mono text-xs tabular text-ink-soft whitespace-nowrap'>
                    <DateTime value={log.created_at} />
                  </td>
                  <td className='px-3 py-3'>
                    <span className='flex items-center gap-2.5 font-display text-sm font-semibold whitespace-nowrap'>
                      <AgentDot type={log.agent_type} />
                      {AGENT_LABEL[log.agent_type] || log.agent_type}
                    </span>
                  </td>
                  <td className='px-3 py-3 text-sm text-ink'>{log.action.replace(/_/g, ' ')}</td>
                  <td className='px-3 py-3 text-sm text-ink-soft hidden sm:table-cell max-w-[320px] truncate'>
                    {log.result || '—'}
                  </td>
                  <td className='px-5 py-3 text-right'>
                    <StatusTicket status={log.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}