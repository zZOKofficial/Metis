'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { Order } from '@/types';

export default function OrdersPage() {
  const { businessId } = useBusiness();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!businessId) return;
    loadOrders();
  }, [businessId]);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/orders/${businessId}`);
      setOrders(res.data);
    } catch {
      console.error('Failed to load orders.');
    } finally {
      setLoading(false);
    }
  };

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  const statusColors: Record<string, string> = {
    pending: 'badge-yellow', confirmed: 'badge-blue', processing: 'badge-blue',
    shipped: 'badge-purple', delivered: 'badge-green', cancelled: 'badge-red',
  };

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>Orders</h1>
        <button onClick={loadOrders} className='btn-secondary'>Refresh</button>
      </div>

      {loading ? (
        <div className='card text-center py-12'><p className='text-slate-400'>Loading orders...</p></div>
      ) : orders.length === 0 ? (
        <div className='card text-center py-12'><p className='text-slate-400'>No orders yet.</p></div>
      ) : (
        <div className='space-y-4'>
          {orders.map((order) => (
            <div key={order.id} className='card'>
              <div className='flex items-start justify-between mb-3'>
                <div>
                  <p className='font-semibold text-slate-800'>Order #{order.id.slice(0, 8)}</p>
                  <p className='text-xs text-slate-400'>{new Date(order.created_at).toLocaleString()}</p>
                </div>
                <span className={`badge ${statusColors[order.status] || 'badge-blue'}`}>{order.status}</span>
              </div>
              <div className='space-y-2 mb-3'>
                {order.items?.map((item, i) => (
                  <div key={i} className='flex items-center justify-between text-sm'>
                    <span className='text-slate-600'>{item.product_name} x{item.quantity}</span>
                    <span className='text-slate-700 font-medium'>৳{item.total_price.toLocaleString()}</span>
                  </div>
                ))}
              </div>
              <div className='pt-3 border-t border-slate-100 flex items-center justify-between'>
                <span className='text-sm text-slate-500'>{order.items?.length || 0} items</span>
                <span className='text-lg font-bold text-metis-600'>৳{order.total_amount.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
