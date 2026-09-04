'use client';

import { useEffect, useRef, useState } from 'react';
import { clearAiConfig, saveAiConfig } from '@/lib/api';
import { AiKeySource, ModelInfo } from '@/types';

const WARN_COLOR = '#b07a2e';

function shortModelName(info: ModelInfo | undefined, fallback: string): string {
  const raw = info?.name || fallback || 'Gemini';
  return raw.replace(/^Gemini\s+/i, '').replace(/\s*\([^)]*\)\s*$/, '').trim();
}

function dotTone(keySource: AiKeySource, verified: boolean): { color: string; label: string } {
  if (keySource === 'user' && verified) {
    return { color: 'var(--ok)', label: 'Your key · verified' };
  }
  if (keySource === 'user') {
    return { color: WARN_COLOR, label: 'Your key · saved, unverified' };
  }
  if (keySource === 'env') {
    return { color: WARN_COLOR, label: 'Server default key · active' };
  }
  if (keySource === 'mock') {
    return { color: 'var(--ok)', label: 'Mock AI mode · no key needed' };
  }
  return { color: 'var(--stamp)', label: 'No key · not connected' };
}

interface GeminiKeyPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  models: ModelInfo[];
  model: string;
  onModelChange: (model: string) => void;
  keySource: AiKeySource;
  verified: boolean;
  onSaved: () => void;
  onCleared: () => void;
}

export default function GeminiKeyPanel({
  open,
  onOpenChange,
  models,
  model,
  onModelChange,
  keySource,
  verified,
  onSaved,
  onCleared,
}: GeminiKeyPanelProps) {
  const [apiKey, setApiKey] = useState('');
  const [reveal, setReveal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);

  const tone = dotTone(keySource, verified);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        onOpenChange(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, onOpenChange]);

  const handleSave = async () => {
    const key = apiKey.trim();
    if (!key || saving) return;
    setSaving(true);
    setError('');
    try {
      await saveAiConfig(key);
      setApiKey('');
      onSaved();
    } catch {
      setError("Couldn't reach the backend — is it running?");
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    if (saving) return;
    setSaving(true);
    setError('');
    try {
      await clearAiConfig();
      setApiKey('');
      onCleared();
    } catch {
      setError("Couldn't reach the backend — is it running?");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div ref={wrapRef} className='relative'>
      <button
        type='button'
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
        aria-label='AI connection settings'
        className='flex items-center gap-2 bg-card border border-ink px-3 py-2 shadow-print-sm cursor-pointer hover:translate-x-[1px] hover:translate-y-[1px] active:translate-x-[1.5px] active:translate-y-[1.5px] transition-transform'
      >
        <span aria-hidden className='w-2 h-2 rounded-full shrink-0' style={{ background: tone.color }} />
        <span className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink'>
          {shortModelName(models.find((m) => m.id === model), model)}
        </span>
        <span aria-hidden className='text-[9px] text-ink-faint leading-none'>
          ▾
        </span>
      </button>

      {open && (
        <div className='absolute right-0 top-[calc(100%+10px)] z-20 w-[300px] sm:w-[330px] fade-up'>
          <div className='ledger p-5'>
            <div className='flex items-center justify-between gap-3'>
              <p className='kicker'>Utility line · private</p>
              <button
                type='button'
                onClick={() => onOpenChange(false)}
                className='kicker cursor-pointer hover:text-ink transition-colors'
              >
                Close ✕
              </button>
            </div>
            <h2 className='font-display text-lg font-bold tracking-tight mt-1'>AI connection</h2>

            <p className='font-mono text-[11px] uppercase tracking-[0.12em] mt-3 flex items-center gap-2'>
              <span aria-hidden className='w-2 h-2 rounded-full shrink-0' style={{ background: tone.color }} />
              <span className='text-ink-soft'>{tone.label}</span>
            </p>

            <div className='mt-4'>
              <label className='label mb-1' htmlFor='ai-key-input'>
                Gemini API key
              </label>
              <div className='flex items-end gap-2'>
                <input
                  id='ai-key-input'
                  type={reveal ? 'text' : 'password'}
                  className='field flex-1 min-w-0 font-mono'
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder='Paste key…'
                  autoComplete='off'
                  spellCheck={false}
                />
                <button
                  type='button'
                  onClick={() => setReveal(!reveal)}
                  className='btn btn-ghost !px-2.5 !py-1.5 text-[10px] shrink-0'
                >
                  {reveal ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <div className='mt-4'>
              <label className='label mb-1' htmlFor='ai-model'>
                Model
              </label>
              <select
                id='ai-model'
                className='field cursor-pointer'
                value={model}
                onChange={(e) => onModelChange(e.target.value)}
              >
                {models.length === 0 && <option value={model}>{model}</option>}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            <div className='flex gap-2 mt-5'>
              <button
                type='button'
                onClick={handleSave}
                disabled={saving || !apiKey.trim()}
                className='btn btn-primary flex-1'
              >
                {saving ? 'Connecting…' : 'Save & connect'}
              </button>
              {keySource === 'user' && (
                <button type='button' onClick={handleClear} disabled={saving} className='btn btn-danger-ghost'>
                  Clear
                </button>
              )}
            </div>

            <p className='font-mono text-[10px] leading-relaxed text-ink-faint mt-3'>
              Saved keys are kept on the server, never in the ledger.
            </p>
            {error && (
              <p className='font-mono text-[11px] text-[var(--stamp)] mt-2' role='alert'>
                {error}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}