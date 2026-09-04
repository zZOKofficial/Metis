'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuthProvider, useAuth } from '@/lib/AuthContext';

type Mode = 'signin' | 'signup' | 'reset';

const COPY: Record<Mode, { form: string; title: string; blurb: string; action: string }> = {
  signin: {
    form: 'Form no. 00 · staff entrance',
    title: 'Sign in to the shop',
    blurb: 'Your books, your staff, your customers — behind one door.',
    action: 'Sign in',
  },
  signup: {
    form: 'Form no. 00 · new proprietor',
    title: 'Open an account',
    blurb: 'Register once. Then hire the six specialists and open the books.',
    action: 'Create account',
  },
  reset: {
    form: 'Form no. 00 · lost key',
    title: 'Reset your password',
    blurb: 'We’ll send a reset link to the address on file.',
    action: 'Send reset link',
  },
};

/** Firebase error codes are not something to show a shopkeeper. */
function readableError(err: any): string {
  const code = err?.code || '';
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return 'That email and password don’t match an account.';
    case 'auth/email-already-in-use':
      return 'An account already exists for that email. Try signing in.';
    case 'auth/weak-password':
      return 'Password is too short — use at least six characters.';
    case 'auth/invalid-email':
      return 'That doesn’t look like a valid email address.';
    case 'auth/too-many-requests':
      return 'Too many attempts. Wait a moment and try again.';
    case 'auth/network-request-failed':
      return 'Couldn’t reach the authentication service. Check your connection.';
    default:
      return err?.message || 'Something went wrong. Try again.';
  }
}

function LoginForm() {
  const router = useRouter();
  const { user, loading, enabled, signIn, signUp, resetPassword } = useAuth();

  const [mode, setMode] = useState<Mode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  // Already signed in, or auth isn't configured at all: there is nothing to do
  // on this page.
  useEffect(() => {
    if (!loading && (user || !enabled)) router.replace('/');
  }, [user, loading, enabled, router]);

  const copy = COPY[mode];

  const switchTo = (next: Mode) => {
    setMode(next);
    setError('');
    setNotice('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setNotice('');
    setBusy(true);
    try {
      if (mode === 'signin') {
        await signIn(email.trim(), password);
        router.replace('/');
      } else if (mode === 'signup') {
        await signUp(email.trim(), password);
        router.replace('/');
      } else {
        await resetPassword(email.trim());
        setNotice('Reset link sent. Check your inbox.');
      }
    } catch (err) {
      setError(readableError(err));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className='ledger p-10 text-center'>
        <p className='font-mono text-xs uppercase tracking-[0.16em] text-ink-soft'>
          checking your credentials…
        </p>
      </div>
    );
  }

  return (
    <div className='ledger p-6 sm:p-10'>
      <p className='kicker mb-1.5'>{copy.form}</p>
      <h1 className='font-display text-3xl font-bold tracking-tight'>{copy.title}</h1>
      <p className='text-ink-soft text-[15px] mt-2 leading-relaxed'>{copy.blurb}</p>

      <form onSubmit={handleSubmit} className='space-y-6 mt-8'>
        <div>
          <label className='label mb-1' htmlFor='auth-email'>
            Email
          </label>
          <input
            id='auth-email'
            type='email'
            autoComplete='email'
            required
            className='field'
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder='owner@yourshop.com'
          />
        </div>

        {mode !== 'reset' && (
          <div>
            <label className='label mb-1' htmlFor='auth-password'>
              Password
            </label>
            <input
              id='auth-password'
              type='password'
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              required
              minLength={6}
              className='field'
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder='••••••••'
            />
          </div>
        )}

        {error && (
          <p role='alert' className='font-mono text-xs tracking-[0.04em] text-stamp'>
            {error}
          </p>
        )}
        {notice && (
          <p role='status' className='font-mono text-xs tracking-[0.04em] text-ink-soft'>
            {notice}
          </p>
        )}

        <button type='submit' disabled={busy} className='btn btn-primary w-full'>
          {busy ? 'Working…' : copy.action}
        </button>
      </form>

      <div className='mt-6 flex flex-wrap items-center justify-between gap-3'>
        {mode === 'signin' ? (
          <>
            <button type='button' className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft hover:text-ink underline underline-offset-4' onClick={() => switchTo('signup')}>
              Open an account
            </button>
            <button type='button' className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft hover:text-ink underline underline-offset-4' onClick={() => switchTo('reset')}>
              Forgot password?
            </button>
          </>
        ) : (
          <button type='button' className='font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft hover:text-ink underline underline-offset-4' onClick={() => switchTo('signin')}>
            ← Back to sign in
          </button>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthProvider>
      <div className='min-h-screen bg-ink px-4 py-10 sm:py-16'>
        <div className='max-w-md mx-auto'>
          <LoginForm />
          <p className='font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint text-center mt-6'>
            Μῆτις · think. act. grow. · an OxyOrb product
          </p>
        </div>
      </div>
    </AuthProvider>
  );
}
