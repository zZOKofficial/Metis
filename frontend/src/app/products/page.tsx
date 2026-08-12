'use client';

import { useEffect, useState } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { Product } from '@/types';

export default function ProductsPage() {
  const { businessId } = useBusiness();
  const [products, setProducts] = useState<Product[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ name: '', description: '', price: '', stock: '', category: '' });

  useEffect(() => {
    if (!businessId) return;
    loadProducts();
  }, [businessId]);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/products/${businessId}`);
      setProducts(res.data);
    } catch {
      console.error('Failed to load products.');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!form.name || !form.price) return alert('Name and price are required.');
    try {
      await api.post(`/products/${businessId}`, {
        name: form.name,
        description: form.description,
        price: parseFloat(form.price),
        stock: parseInt(form.stock) || 0,
        category: form.category,
        status: 'active',
        variants: [],
      });
      setForm({ name: '', description: '', price: '', stock: '', category: '' });
      setShowForm(false);
      loadProducts();
      notifyDataChanged();
    } catch {
      alert('Failed to add product.');
    }
  };

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  return (
    <div className='space-y-6'>
      <div className='flex items-center justify-between'>
        <h1 className='text-2xl font-bold text-slate-800'>Products</h1>
        <button onClick={() => setShowForm(!showForm)} className='btn-primary'>+ Add Product</button>
      </div>

      {showForm && (
        <div className='card'>
          <h3 className='font-semibold mb-4'>New Product</h3>
          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Name</label>
              <input className='input' value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder='Product name' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Category</label>
              <input className='input' value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder='e.g., Shirts' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Price (৳)</label>
              <input className='input' type='number' value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder='0.00' />
            </div>
            <div>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Stock</label>
              <input className='input' type='number' value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} placeholder='0' />
            </div>
            <div className='md:col-span-2'>
              <label className='block text-sm font-medium text-slate-700 mb-1'>Description</label>
              <textarea className='input' rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder='Product description' />
            </div>
          </div>
          <div className='flex gap-3 mt-4'>
            <button onClick={() => setShowForm(false)} className='btn-secondary'>Cancel</button>
            <button onClick={handleAdd} className='btn-primary'>Save Product</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className='card text-center py-12'><p className='text-slate-400'>Loading products...</p></div>
      ) : products.length === 0 ? (
        <div className='card text-center py-12'><p className='text-slate-400'>No products yet. Add your first product above.</p></div>
      ) : (
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
          {products.map((product) => (
            <div key={product.id} className='card'>
              <div className='flex items-start justify-between mb-2'>
                <h3 className='font-semibold text-slate-800'>{product.name}</h3>
                <span className={`badge ${product.stock > 5 ? 'badge-green' : product.stock > 0 ? 'badge-yellow' : 'badge-red'}`}>
                  {product.stock} in stock
                </span>
              </div>
              <p className='text-sm text-slate-500 mb-3 line-clamp-2'>{product.description || 'No description'}</p>
              <div className='flex items-center justify-between pt-3 border-t border-slate-100'>
                <span className='text-lg font-bold text-metis-600'>৳{product.price.toLocaleString()}</span>
                <span className='text-xs text-slate-400'>{product.category}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
