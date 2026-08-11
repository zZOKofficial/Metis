'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { Approval } from '@/types';

export default function ApprovalsPage() {
  const { businessId } = useBusiness();
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!businessId) return;
    loadApprovals();
  }, [businessId]);

  const loadApprovals = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/approvals/${businessId}`);
      setApprovals(res.data);
    } catch {
      console.error('Failed to load approvals.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/approvals/${businessId}/${id}/approve`);
      loadApprovals();
    } catch {
      alert('Failed to approve.');
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.post(`/approvals/${businessId}/${id}/reject`);
      loadApprovals();
    } catch {
      alert('Failed to reject.');
    }
  };

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  const riskColors: Record<string, string> = { low: 'badge-green', medium: 'badge-yellow', high: 'badge-red' };
  const pending = approvals.filter(a => a.status === 'pending');
  const history = approvals.filter(a => a.status !== 'pending');

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>Approval Center</h1>
        <button onClick={loadApprovals} className='btn-secondary'>Refresh</button>
      </div>

      {loading ? (
        <div className='card text-center py-12'><p className='text-slate-400'>Loading...</p></div>
      ) : pending.length === 0 ? (
        <div className='card text-center py-12'>
          <p className='text-slate-400 text-lg'>No pending approvals</p>
          <p className='text-slate-400 text-sm mt-2'>Agent actions requiring approval will appear here.</p>
        </div>
      ) : (
        <div className='space-y-4'>
          {pending.map((approval) => (
            <div key={approval.id} className='card'>
              <div className='flex items-start justify-between mb-3'>
                <div>
                  <div className='flex items-center gap-2 mb-1'>
                    <h3 className='font-semibold text-slate-800'>{approval.action}</h3>
                    <span className={`badge ${riskColors[approval.risk_level] || 'badge-yellow'}`}>{approval.risk_level}</span>
                  </div>
                  <p className='text-sm text-slate-500'>Requested by: {approval.agent_type}</p>
                </div>
              </div>
              <p className='text-sm text-slate-600 mb-4 bg-slate-50 rounded-lg p-3'>{approval.reason}</p>
              <div className='flex gap-3'>
                <button onClick={() => handleApprove(approval.id)} className='btn-primary flex-1'>Approve</button>
                <button onClick={() => handleReject(approval.id)} className='btn-danger flex-1'>Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {history.length > 0 && (
        <div>
          <h2 className='text-lg font-semibold text-slate-700 mb-3'>History</h2>
          <div className='space-y-2'>
            {history.slice(0, 10).map((approval) => (
              <div key={approval.id} className='flex items-center justify-between p-3 bg-slate-50 rounded-lg'>
                <div className='flex items-center gap-3'>
                  <span className={`badge ${approval.status === 'approved' ? 'badge-green' : 'badge-red'}`}>{approval.status}</span>
                  <span className='text-sm text-slate-700'>{approval.action}</span>
                </div>
                <span className='text-xs text-slate-400'>{approval.agent_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
