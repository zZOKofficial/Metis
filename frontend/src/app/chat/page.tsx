'use client';

import { useState, useRef, useEffect } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { ChatMessage } from '@/types';

export default function ChatPage() {
  const { businessId } = useBusiness();
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I am your Manager Agent. How can I help your business today? You can ask me about sales, inventory, marketing campaigns, or any business question.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading || !businessId) return;
    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.post(`/chat/${businessId}`, {
        business_id: businessId,
        message: input,
      });
      const assistantMessage: ChatMessage = { role: 'assistant', content: res.data.message };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please make sure the backend is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  return (
    <div className='h-full flex flex-col'>
      <div className='flex items-center justify-between mb-4'>
        <h1 className='text-2xl font-bold text-slate-800'>Business Chat</h1>
        <span className='badge badge-blue'>Manager Agent</span>
      </div>

      <div className='flex-1 card flex flex-col overflow-hidden'>
        <div className='flex-1 overflow-y-auto p-4 space-y-4'>
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-metis-500 text-white' : 'bg-slate-100 text-slate-800'}`}>
                <p className='text-sm whitespace-pre-wrap'>{msg.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className='flex justify-start'>
              <div className='bg-slate-100 rounded-2xl px-4 py-3'>
                <div className='flex gap-1'>
                  <span className='w-2 h-2 bg-slate-400 rounded-full animate-bounce' style={{ animationDelay: '0ms' }}></span>
                  <span className='w-2 h-2 bg-slate-400 rounded-full animate-bounce' style={{ animationDelay: '150ms' }}></span>
                  <span className='w-2 h-2 bg-slate-400 rounded-full animate-bounce' style={{ animationDelay: '300ms' }}></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className='border-t border-slate-200 p-4'>
          <div className='flex gap-3'>
            <input
              className='input flex-1'
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder='Ask your Manager Agent...'
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()} className='btn-primary'>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
