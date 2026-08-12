'use client';

import { useState, useRef, useEffect } from 'react';
import { useBusiness } from '@/lib/BusinessContext';
import api from '@/lib/api';
import { notifyDataChanged } from '@/lib/refresh';
import { ChatMessage, ModelInfo } from '@/types';
import Markdown from '@/components/Markdown';
import { AgentDot } from '@/components/ui';

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

  if (!businessId) {
    return (
      <p className='font-mono text-xs uppercase tracking-[0.14em] text-ink-faint mt-10 text-center'>
        Please set up your business first.
      </p>
    );
  }

  return (
    <div className='h-full flex flex-col' style={{ minHeight: 'calc(100vh - 100px)' }}>
      <div className='flex items-end justify-between gap-3 flex-wrap mb-5'>
        <div>
          <p className='kicker mb-1.5'>Inter-office correspondence · confidential</p>
          <h1 className='font-display text-3xl sm:text-4xl font-bold tracking-tight'>Business Chat</h1>
        </div>
        <div className='flex items-center gap-3'>
          <label htmlFor='chat-model' className='kicker'>
            Model
          </label>
          <select id='chat-model' value={model} onChange={handleModelChange} disabled={loading} className='field !w-auto cursor-pointer text-sm'>
            {models.length === 0 && <option value={model}>{model}</option>}
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className='ledger flex flex-col min-h-0 flex-1'>
        <div className='flex items-center justify-between border-b border-[var(--rule)] px-5 py-3'>
          <span className='flex items-center gap-2.5'>
            <AgentDot type='manager' />
            <span className='font-display text-sm font-semibold'>Manager Agent</span>
          </span>
          <span className='font-mono text-[10px] uppercase tracking-[0.18em] text-ok'>● on duty</span>
        </div>

        <div className='flex-1 overflow-y-auto p-5 sm:p-7 space-y-6' aria-live='polite'>
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'user' ? (
                <div className='max-w-[85%] sm:max-w-[70%] bg-ink text-card px-4 py-3 shadow-print-sm'>
                  <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-card/50 mb-1.5'>
                    You · the owner
                  </p>
                  <p className='text-[15px] leading-relaxed whitespace-pre-wrap'>{msg.content}</p>
                </div>
              ) : (
                <div className='max-w-[85%] sm:max-w-[75%] bg-card border border-ink border-l-[3px] border-l-carbon px-4 py-3 shadow-print-sm'>
                  <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-carbon mb-1.5'>
                    From the manager
                  </p>
                  <Markdown content={msg.content} />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className='flex justify-start'>
              <div className='bg-card border border-ink border-l-[3px] border-l-carbon px-4 py-3 shadow-print-sm'>
                <div className='flex gap-1.5 py-0.5'>
                  <span className='w-1.5 h-1.5 bg-ink/50 blink'></span>
                  <span className='w-1.5 h-1.5 bg-ink/50 blink' style={{ animationDelay: '0.2s' }}></span>
                  <span className='w-1.5 h-1.5 bg-ink/50 blink' style={{ animationDelay: '0.4s' }}></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className='border-t border-[var(--rule)] p-4 sm:p-5'>
          <form
            className='flex items-end gap-3'
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
          >
            <div className='flex-1 min-w-0'>
              <label htmlFor='chat-input' className='kicker block mb-1'>
                Your instruction to the manager
              </label>
              <input
                id='chat-input'
                className='field !border-b-2'
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder='How is my business doing today?'
                disabled={loading}
              />
            </div>
            <button type='submit' disabled={loading || !input.trim()} className='btn btn-primary shrink-0'>
              Send →
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}