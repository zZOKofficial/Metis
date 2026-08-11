'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { AgentLog } from '@/types';

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

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  const agentColors: Record<string, string> = {
    manager: 'bg-blue-500', sales: 'bg-green-500', support: 'bg-purple-500',
    marketing: 'bg-orange-500', operations: 'bg-teal-500', analytics: 'bg-pink-500',
  };

  const formatTime = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return ''; }
  };

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>Activity Feed</h1>
        <button onClick={loadActivity} className='btn-secondary'>Refresh</button>
      </div>

      <div className='card'>
        {loading ? (
          <p className='text-slate-400 text-center py-8'>Loading activity...</p>
        ) : logs.length === 0 ? (
          <p className='text-slate-400 text-center py-8'>No activity yet. Agent actions will appear here.</p>
        ) : (
          <div className='space-y-1'>
            {logs.map((log) => (
              <div key={log.id} className='flex items-start gap-3 p-3 hover:bg-slate-50 rounded-lg transition-colors'>
                <div className={`w-2 h-2 rounded-full mt-2 ${agentColors[log.agent_type] || 'bg-slate-400'}`} />
                <div className='flex-1 min-w-0'>
                  <div className='flex items-center gap-2'>
                    <span className='text-sm font-medium text-slate-700 capitalize'>{log.agent_type}</span>
                    <span className='text-xs text-slate-400'>{formatTime(log.created_at)}</span>
                  </div>
                  <p className='text-sm text-slate-600'>{log.action.replace(/_/g, ' ')}</p>
                  {log.result && <p className='text-xs text-slate-400 mt-1 truncate'>{log.result}</p>}
                </div>
                <span className={`badge ${log.status === 'completed' ? 'badge-green' : 'badge-yellow'}`}>
                  {log.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
