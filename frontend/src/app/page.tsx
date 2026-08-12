'use client';

import { useCallback, useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { useDataRefresh } from '@/lib/refresh';
import { DashboardMetrics, AgentStatus } from '@/types';
import SetupWizard from '@/components/SetupWizard';

export default function DashboardPage() {
  const { businessId, currentBusiness } = useBusiness();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return <div className='flex items-center justify-center h-full'><p className='text-slate-500'>Loading dashboard...</p></div>;
  }

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>{currentBusiness?.name || 'Dashboard'}</h1>
        <button onClick={loadData} className='btn-secondary'>Refresh</button>
      </div>

      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
        <MetricCard title='Revenue' value={`৳${(metrics?.total_revenue || 0).toLocaleString()}`} subtitle='Total revenue' color='blue' />
        <MetricCard title='Orders' value={metrics?.total_orders || 0} subtitle='Total orders' color='green' />
        <MetricCard title='Customers' value={metrics?.total_customers || 0} subtitle='Total customers' color='purple' />
        <MetricCard title='Conversion' value={`${metrics?.conversion_rate || 0}%`} subtitle='Conversion rate' color='orange' />
      </div>

      <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
        <div className='card'>
          <h3 className='font-semibold text-slate-800 mb-4'>AI Recommendations</h3>
          <div className='space-y-3'>
            {metrics?.recommendations?.map((rec, i) => (
              <div key={i} className='flex items-start gap-3 p-3 bg-slate-50 rounded-lg'>
                <span className='text-metis-500 mt-0.5'>→</span>
                <p className='text-sm text-slate-600'>{rec}</p>
              </div>
            )) || <p className='text-slate-400 text-sm'>No recommendations yet.</p>}
          </div>
        </div>

        <div className='card'>
          <h3 className='font-semibold text-slate-800 mb-4'>Agent Activity</h3>
          <div className='space-y-3'>
            {agents.map((agent) => (
              <div key={agent.type} className='flex items-center justify-between p-3 bg-slate-50 rounded-lg'>
                <div className='flex items-center gap-3'>
                  <span className='w-2 h-2 bg-green-500 rounded-full'></span>
                  <span className='text-sm font-medium text-slate-700'>{agent.name}</span>
                </div>
                <span className='text-sm text-slate-500'>{agent.tasks_completed} tasks</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {(metrics?.low_stock_products?.length ?? 0) > 0 && (
        <div className='card border-l-4 border-l-yellow-400'>
          <h3 className='font-semibold text-slate-800 mb-3'>⚠️ Low Stock Alerts</h3>
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3'>
            {metrics?.low_stock_products?.map((p) => (
              <div key={p.id} className='flex items-center justify-between p-3 bg-yellow-50 rounded-lg'>
                <span className='text-sm font-medium text-slate-700'>{p.name}</span>
                <span className='badge badge-yellow'>{p.stock} left</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, subtitle, color }: { title: string; value: string | number; subtitle: string; color: string }) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
  };
  return (
    <div className={`card border ${colors[color]}`}>
      <p className='text-sm font-medium opacity-75'>{title}</p>
      <p className='text-3xl font-bold mt-1'>{value}</p>
      <p className='text-xs mt-1 opacity-60'>{subtitle}</p>
    </div>
  );
}
