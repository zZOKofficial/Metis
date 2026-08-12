'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { AgentStatus } from '@/types';
import { Docket, LoadingState, AgentDot, AGENT_LABEL, AGENT_DESC, AGENT_ORDER } from '@/components/ui';

export default function AgentsPage() {
  const { businessId } = useBusiness();
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!businessId) return;
    loadAgents();
  }, [businessId]);

  const loadAgents = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/agents/${businessId}`);
      setAgents(res.data);
    } catch {
      console.error('Failed to load agents.');
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

  const byType = new Map(agents.map((a) => [a.type, a]));
  const roster = AGENT_ORDER.map((type) => byType.get(type)).filter(Boolean) as AgentStatus[];

  return (
    <div className='space-y-8'>
      <Docket
        title='Agent Center'
        memo='staffing board · six specialists on the clock'
        action={
          <button onClick={loadAgents} className='btn btn-ghost'>
            ↻ Recheck
          </button>
        }
      />

      {loading ? (
        <LoadingState label='reading personnel files…' />
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-7'>
          {roster.map((agent) => (
            <article key={agent.type} className='ledger p-5 flex flex-col'>
              <header className='flex items-start justify-between gap-3'>
                <div className='flex items-center gap-3'>
                  <span className='inline-flex items-center justify-center w-9 h-9 border border-ink'>
                    <AgentDot type={agent.type} className='w-3 h-3' />
                  </span>
                  <div>
                    <h2 className='font-display text-lg font-bold leading-tight'>
                      {AGENT_LABEL[agent.type] || agent.name}
                    </h2>
                    <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint'>
                      {agent.type} agent
                    </p>
                  </div>
                </div>
                {agent.type === 'manager' && <span className='ticket ticket--carbon'>lead</span>}
              </header>

              <p className='text-sm text-ink-soft leading-relaxed mt-4'>
                {AGENT_DESC[agent.type] || agent.type}
              </p>

              <dl className='mt-5 pt-4 border-t border-[var(--rule)] flex items-center justify-between'>
                <dt className='kicker'>Tasks completed</dt>
                <dd className='font-mono text-xl font-semibold tabular'>{agent.tasks_completed}</dd>
              </dl>

              <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-ok mt-3'>
                ● on duty — takes responsibility
              </p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}