'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { streamChat } from '@/lib/sse';
import { useStreamBatcher } from '@/lib/useStreamBatcher';
import { Business, ChatMessage, Product } from '@/types';
import Markdown from '@/components/Markdown';
import { Cash, AgentDot } from '@/components/ui';

const sessionKey = (businessId: string) => `metis_storefront_${businessId}_session`;
const shopperKey = (businessId: string) => `metis_storefront_${businessId}_shopper`;

const GREETING: ChatMessage = {
  role: 'assistant',
  content: 'Welcome in — ask me about anything on the shelves. I can check stock, recommend something, and put together an order for you.',
};

function loadJson<T>(key: string): T | null {
  try {
    const saved = localStorage.getItem(key);
    if (!saved) return null;
    return JSON.parse(saved) as T;
  } catch {
    return null;
  }
}

function saveJson(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage failures (e.g. quota exceeded)
  }
}

function getOrCreateSessionId(businessId: string): string {
  const key = sessionKey(businessId);
  const existing = loadJson<{ id: string }>(key);
  if (existing?.id) return existing.id;
  const id =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  saveJson(key, { id });
  return id;
}

export default function StorefrontPage() {
  const params = useParams<{ businessId: string }>();
  const businessId = params.businessId;

  const [sessionId, setSessionId] = useState<string>('');
  const [business, setBusiness] = useState<Business | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [shopper, setShopper] = useState<{ customer_id: string; name: string } | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [entering, setEntering] = useState(false);
  const [entryError, setEntryError] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const streamBatcher = useStreamBatcher();
  const [notice, setNotice] = useState('');
  const [loadError, setLoadError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!businessId) return;
    const savedShopper = loadJson<{ customer_id: string; name: string }>(shopperKey(businessId));
    setShopper(savedShopper?.customer_id ? savedShopper : null);
  }, [businessId]);

  useEffect(() => {
    if (!businessId) return;
    const sid = getOrCreateSessionId(businessId);
    setSessionId(sid);
    setMessages([GREETING]);
    let cancelled = false;
    api
      .get(`/business/${businessId}`)
      .then((res) => {
        if (!cancelled) setBusiness(res.data);
      })
      .catch(() => {
        if (!cancelled) setLoadError('This store could not be found.');
      });
    api
      .get(`/products/${businessId}?in_stock=true`)
      .then((res) => {
        if (!cancelled) setProducts(res.data);
      })
      .catch(() => {
        // Catalog is a nicety; chat still works without it
      });
    // Session-scoped server history survives page reloads
    api
      .get(`/storefront/${businessId}/history?session_id=${encodeURIComponent(sid)}&limit=50`)
      .then((res) => {
        if (cancelled) return;
        const serverMessages: ChatMessage[] = (res.data || []).map((m: any) => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || m.created_at,
        }));
        if (serverMessages.length > 0) setMessages(serverMessages);
      })
      .catch(() => {
        // Fall back to the greeting
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [businessId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, streamBatcher.text]);

  const enterStore = async () => {
    const trimmed = name.trim();
    if (!trimmed || entering) return;
    setEntering(true);
    setEntryError('');
    try {
      const res = await api.post(`/customers/${businessId}`, { name: trimmed, email: email.trim() });
      const customer_id = res.data?.id;
      if (!customer_id) throw new Error('No customer id');
      const saved = { customer_id, name: trimmed };
      saveJson(shopperKey(businessId), saved);
      setShopper(saved);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Nice to meet you, ${trimmed}! What can I help you find today?`,
        },
      ]);
    } catch {
      setEntryError("Couldn't check you in — is the store's backend running?");
    } finally {
      setEntering(false);
    }
  };

  const sendMessage = useCallback(async () => {
    if (!input.trim() || loading || !businessId) return;
    const userMessage: ChatMessage = { role: 'user', content: input, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setStreaming(true);
    setNotice('');
    streamBatcher.reset();

    await streamChat(
      `/storefront/${businessId}/chat/stream`,
      {
        business_id: businessId,
        session_id: sessionId,
        customer_id: shopper?.customer_id || '',
        message: userMessage.content,
        history: messages.map((m) => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
      },
      {
        onDelta: (text) => streamBatcher.push(text),
        onDone: (response) => {
          const staged = (response.agent_actions || []).some(
            (a: any) => a.status === 'staged' && a.approval_id
          );
          if (staged) {
            setNotice('Your order is being confirmed by the store — the owner has been asked to authorise it.');
          }
          if (Array.isArray(response.history) && response.history.length > 0) {
            setMessages(
              response.history.map((m: any) => ({
                role: m.role,
                content: m.content,
                timestamp: m.timestamp,
              }))
            );
          } else {
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: response.message, timestamp: new Date().toISOString() },
            ]);
          }
          setStreaming(false);
          setLoading(false);
          streamBatcher.reset();
        },
        onError: () => {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: 'Sorry, the shop assistant is unreachable right now. Please try again in a moment.' },
          ]);
          setStreaming(false);
          setLoading(false);
          streamBatcher.reset();
        },
      }
    );
  }, [businessId, sessionId, shopper, input, loading, messages, streamBatcher]);

  if (loadError) {
    return (
      <div className='min-h-screen bg-ink flex items-center justify-center p-6'>
        <div className='ledger p-10 text-center max-w-md'>
          <p className='kicker mb-1.5'>Storefront · no such shop</p>
          <h1 className='font-display text-2xl font-bold text-ink'>Store not found</h1>
          <p className='text-ink-soft text-[15px] mt-3'>{loadError}</p>
          <Link href='/' className='btn btn-ghost mt-6'>
            ← Back to METIS
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className='min-h-screen bg-ink flex flex-col'>
      <header className='bg-ink text-card border-b border-white/10'>
        <div className='mx-auto max-w-5xl w-full flex items-center justify-between gap-3 px-4 sm:px-8 py-4'>
          <div className='min-w-0'>
            <p className='font-mono text-[10px] uppercase tracking-[0.24em] text-card/50'>{business?.category || 'General store'} · storefront</p>
            <h1 className='font-display text-xl sm:text-2xl font-extrabold tracking-tight truncate'>
              {business?.name || 'The shop'}
            </h1>
          </div>
          <div className='flex items-center gap-3 shrink-0'>
            <span className='ticket ticket--carbon hidden sm:inline-flex'>{business?.category || 'general store'}</span>
            <Link href='/' className='font-mono text-[10px] uppercase tracking-[0.14em] text-card/60 border border-card/25 px-2.5 py-1 hover:text-card hover:border-card/60 transition-colors'>
              Owner console →
            </Link>
          </div>
        </div>
      </header>

      <main className='desk flex-1'>
        <div className='mx-auto max-w-5xl w-full px-4 sm:px-8 py-6 sm:py-10 space-y-6'>
          {!shopper ? (
            <section className='ledger max-w-xl mx-auto p-6 sm:p-8'>
              <p className='kicker mb-1.5'>Check-in · first visit</p>
              <h2 className='font-display text-2xl font-bold text-ink tracking-tight'>Before we talk shop</h2>
              <p className='text-ink-soft text-[15px] mt-2 leading-relaxed'>
                Give us a name so the assistant can place orders on your account. That&apos;s all we need.
              </p>
              <form
                className='mt-6 grid gap-5'
                onSubmit={(e) => {
                  e.preventDefault();
                  enterStore();
                }}
              >
                <div>
                  <label className='label mb-1' htmlFor='sf-name'>
                    Your name
                  </label>
                  <input
                    id='sf-name'
                    className='field'
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder='e.g. P. Parker'
                    autoComplete='name'
                    spellCheck={false}
                  />
                </div>
                <div>
                  <label className='label mb-1' htmlFor='sf-email'>
                    Email <span className='text-ink-faint normal-case'>(optional)</span>
                  </label>
                  <input
                    id='sf-email'
                    type='email'
                    className='field'
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder='you@example.com'
                    autoComplete='email'
                  />
                </div>
                {entryError && (
                  <p className='font-mono text-[11px] text-[var(--stamp)]' role='alert'>
                    {entryError}
                  </p>
                )}
                <div className='flex justify-end'>
                  <button type='submit' disabled={entering || !name.trim()} className='btn btn-primary'>
                    {entering ? 'Checking in…' : 'Enter the shop →'}
                  </button>
                </div>
              </form>
            </section>
          ) : (
            <>
              {products.length > 0 && (
                <section className='ledger p-5' aria-label='On the shelves'>
                  <div className='flex items-baseline justify-between mb-3'>
                    <h2 className='kicker'>On the shelves · in stock</h2>
                    <span className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint'>
                      {products.length} item{products.length === 1 ? '' : 's'}
                    </span>
                  </div>
                  <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3'>
                    {products.slice(0, 9).map((p) => (
                      <div key={p.id} className='border border-[var(--rule)] bg-paper/60 px-4 py-3'>
                        <div className='flex items-start justify-between gap-2'>
                          <p className='font-display text-[15px] font-semibold text-ink truncate'>{p.name}</p>
                          <Cash value={p.price} currency={business?.currency} className='font-mono text-sm font-semibold text-ink shrink-0' />
                        </div>
                        <p className='font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint mt-1 truncate'>
                          {p.category || 'general'} · {p.stock} in stock
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <div className='ledger flex flex-col min-h-[420px]'>
                <div className='flex items-center justify-between border-b border-[var(--rule)] px-5 py-3'>
                  <span className='flex items-center gap-2.5'>
                    <AgentDot type='sales' />
                    <span className='font-display text-sm font-semibold text-ink'>Sales Assistant</span>
                  </span>
                  <span className='flex items-center gap-3'>
                    <span className='font-mono text-[10px] uppercase tracking-[0.18em] text-ok'>● on the floor</span>
                    <span className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint'>{shopper.name}</span>
                  </span>
                </div>

                <div className='flex-1 overflow-y-auto p-5 sm:p-7 space-y-6 min-h-0 max-h-[520px]' aria-live='polite'>
                  {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      {msg.role === 'user' ? (
                        <div className='max-w-[85%] sm:max-w-[70%] bg-ink text-card px-4 py-3 shadow-print-sm'>
                          <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-card/50 mb-1.5'>
                            You · the shopper
                          </p>
                          <p className='text-[15px] leading-relaxed whitespace-pre-wrap'>{msg.content}</p>
                        </div>
                      ) : (
                        <div className='max-w-[85%] sm:max-w-[75%] bg-card border border-ink border-l-[3px] border-l-agent-sales px-4 py-3 shadow-print-sm'>
                          <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-ink-soft mb-1.5'>
                            From the sales assistant
                          </p>
                          <Markdown content={msg.content} />
                        </div>
                      )}
                    </div>
                  ))}
                  {streaming && (
                    <div className='flex justify-start'>
                      {streamBatcher.text ? (
                        <div className='max-w-[85%] sm:max-w-[75%] bg-card border border-ink border-l-[3px] border-l-agent-sales px-4 py-3 shadow-print-sm'>
                          <p className='font-mono text-[10px] uppercase tracking-[0.16em] text-ink-soft mb-1.5'>
                            From the sales assistant
                          </p>
                          <Markdown content={streamBatcher.text} />
                        </div>
                      ) : (
                        <div className='bg-card border border-ink border-l-[3px] border-l-agent-sales px-4 py-3 shadow-print-sm'>
                          <div className='flex gap-1.5 py-0.5'>
                            <span className='w-1.5 h-1.5 bg-ink/50 blink'></span>
                            <span className='w-1.5 h-1.5 bg-ink/50 blink' style={{ animationDelay: '0.2s' }}></span>
                            <span className='w-1.5 h-1.5 bg-ink/50 blink' style={{ animationDelay: '0.4s' }}></span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {notice && (
                  <p className='mx-5 sm:mx-7 font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--stamp)] border border-dashed border-[var(--stamp)] px-3 py-2'>
                    {notice}
                  </p>
                )}

                <div className='border-t border-[var(--rule)] p-4 sm:p-5'>
                  <form
                    className='flex items-end gap-3'
                    onSubmit={(e) => {
                      e.preventDefault();
                      sendMessage();
                    }}
                  >
                    <div className='flex-1 min-w-0'>
                      <label htmlFor='sf-input' className='kicker block mb-1'>
                        Ask the assistant
                      </label>
                      <input
                        id='sf-input'
                        className='field !border-b-2'
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder='Do you have a Bat-Mobile in stock?'
                        disabled={loading}
                      />
                    </div>
                    <button type='submit' disabled={loading || !input.trim()} className='btn btn-primary shrink-0'>
                      Send →
                    </button>
                  </form>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      <footer className='bg-ink text-card/50 border-t border-white/10'>
        <div className='mx-auto max-w-5xl w-full px-4 sm:px-8 py-4 flex items-center justify-between gap-3 flex-wrap'>
          <p className='font-mono text-[10px] uppercase tracking-[0.2em]'>
            Μῆτις · your business, operated by AI
          </p>
          <p className='font-mono text-[10px] uppercase tracking-[0.14em]'>
            demo storefront · v0.7.2
          </p>
        </div>
      </footer>
    </div>
  );
}