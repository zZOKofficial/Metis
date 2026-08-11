'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { AgentStatus } from '@/types';

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

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  const descriptions: Record<string, string> = {
    manager: 'Orchestrates the workforce, delegates tasks, and coordinates between agents.',
    sales: 'Handles product inquiries, recommendations, and order creation.',
    support: 'Answers customer questions, explains policies, handles complaints.',
    marketing: 'Creates campaigns, generates content, identifies opportunities.',
    operations: 'Manages orders, tracks inventory, monitors fulfillment.',
    analytics: 'Analyzes business data, provides insights and recommendations.',
  };

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>Agent Center</h1>
        <button onClick={loadAgents} className='btn-secondary'>Refresh</button>
      </div>

      {loading ? (
        <div className='card text-center py-12'><p className='text-slate-400'>Loading agents...</p></div>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {agents.map((agent) => (
            <div key={agent.type} className='card hover:shadow-md transition-shadow'>
              <div className='flex items-start justify-between mb-3'>
                <div className='w-10 h-10 bg-metis-100 rounded-lg flex items-center justify-center'>
                  <svg className='w-5 h-5 text-metis-600' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
                    <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' />
                  </svg>
                </div>
                <span className='badge badge-green'>Active</span>
              </div>
              <h3 className='font-semibold text-slate-800'>{agent.name}</h3>
              <p className='text-sm text-slate-500 mt-1'>{descriptions[agent.type]}</p>
              <div className='mt-4 pt-4 border-t border-slate-100 flex items-center justify-between'>
                <span className='text-xs text-slate-400'>Tasks completed</span>
                <span className='text-sm font-medium text-slate-700'>{agent.tasks_completed}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
