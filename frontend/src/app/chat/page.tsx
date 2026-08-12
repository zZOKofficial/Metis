'use client';

import { useState, useRef, useEffect } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { ChatMessage, ModelInfo } from '@/types';
import Markdown from '@/components/Markdown';

const GREETING: ChatMessage = {
  role: 'assistant',
  content: 'Hello! I am your Manager Agent. How can I help your business today? You can ask me about sales, inventory, marketing campaigns, or any business question.',
};

const MAX_SAVED_MESSAGES = 200;
const DEFAULT_MODEL = 'gemini-flash-lite-latest';
const MODEL_STORAGE_KEY = 'metis_chat_model';

const storageKey = (businessId: string) => `metis_chat_${businessId}`;

function loadHistory(businessId: string): ChatMessage[] {
  try {
    const saved = localStorage.getItem(storageKey(businessId));
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {
    // Ignore corrupted storage
  }
  return [GREETING];
}

function saveHistory(businessId: string, messages: ChatMessage[]) {
  try {
    localStorage.setItem(storageKey(businessId), JSON.stringify(messages.slice(-MAX_SAVED_MESSAGES)));
  } catch {
    // Ignore storage failures (e.g. quota exceeded)
  }
}

export default function ChatPage() {
  const { businessId } = useBusiness();
  const [messages, setMessages] = useState<ChatMessage[]>(() => (businessId ? loadHistory(businessId) : [GREETING]));
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState<string>(() => {
    try {
      return localStorage.getItem(MODEL_STORAGE_KEY) || DEFAULT_MODEL;
    } catch {
      return DEFAULT_MODEL;
    }
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .get('/models')
      .then((res) => {
        const available: ModelInfo[] = res.data.models || [];
        setModels(available);
        if (available.length > 0 && !available.some((m) => m.id === model)) {
          setModel(res.data.default || DEFAULT_MODEL);
        }
      })
      .catch(() => {
        // Backend unavailable; fall back to the default model.
      });
  }, []);

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    setModel(value);
    try {
      localStorage.setItem(MODEL_STORAGE_KEY, value);
    } catch {
      // Ignore storage failures
    }
  };

  useEffect(() => {
    if (!businessId) return;
    loadServerHistory();
  }, [businessId]);

  const loadServerHistory = async () => {
    try {
      const res = await api.get(`/chat/${businessId}/history?limit=50`);
      const serverMessages: ChatMessage[] = res.data.map((m: any) => ({
        role: m.role,
        content: m.content,
        timestamp: m.timestamp || m.created_at,
      }));
      if (serverMessages.length > 0) {
        setMessages(serverMessages);
        saveHistory(businessId, serverMessages);
        return;
      }
    } catch {
      // Fall back to local history if backend is unavailable
    }
    setMessages(loadHistory(businessId));
  };

  useEffect(() => {
    if (businessId) saveHistory(businessId, messages);
  }, [messages, businessId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading || !businessId) return;
    const userMessage: ChatMessage = { role: 'user', content: input, timestamp: new Date().toISOString() };
    const fullHistory = [...messages, userMessage];
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.post(`/chat/${businessId}`, {
        business_id: businessId,
        message: input,
        model,
        history: fullHistory.slice(0, -1).map((m) => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
      });
      if (Array.isArray(res.data.history) && res.data.history.length > 0) {
        setMessages(res.data.history.map((m: any) => ({ role: m.role, content: m.content, timestamp: m.timestamp })));
      } else {
        const assistantMessage: ChatMessage = { role: 'assistant', content: res.data.message, timestamp: new Date().toISOString() };
        setMessages((prev) => [...prev, assistantMessage]);
      }
      notifyDataChanged();
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please make sure the backend is running.' }]);
    } finally {
      setLoading(false);
    }
  };

  if (!businessId) return <p className='text-slate-500'>Please set up your business first.</p>;

  return (
    <div className='h-full flex flex-col'>
      <div className='flex items-center justify-between mb-4 gap-3 flex-wrap'>
        <h1 className='text-2xl font-bold text-slate-800'>Business Chat</h1>
        <div className='flex items-center gap-3'>
          <label htmlFor='chat-model' className='text-xs font-medium text-slate-500'>
            Model
          </label>
          <select
            id='chat-model'
            value={model}
            onChange={handleModelChange}
            disabled={loading}
            className='input py-1.5 text-sm'
          >
            {models.length === 0 && <option value={model}>{model}</option>}
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
          <span className='badge badge-blue'>Manager Agent</span>
        </div>
      </div>

      <div className='flex-1 card flex flex-col overflow-hidden'>
        <div className='flex-1 overflow-y-auto p-4 space-y-4'>
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-metis-500 text-white' : 'bg-slate-100 text-slate-800'}`}>
                {msg.role === 'user' ? (
                  <p className='text-sm whitespace-pre-wrap'>{msg.content}</p>
                ) : (
                  <Markdown content={msg.content} />
                )}
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
