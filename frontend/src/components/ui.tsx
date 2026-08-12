'use client';

export const AGENT_ORDER = ['manager', 'sales', 'support', 'marketing', 'operations', 'analytics'] as const;

export const AGENT_LABEL: Record<string, string> = {
  manager: 'Manager',
  sales: 'Sales',
  support: 'Support',
  marketing: 'Marketing',
  operations: 'Operations',
  analytics: 'Analytics',
};

export const AGENT_DESC: Record<string, string> = {
  manager: 'Orchestrates the workforce, delegates tasks, and owns the daily summary.',
  sales: 'Handles product inquiries, recommends, and takes orders.',
  support: 'Answers policy questions and resolves customer issues.',
  marketing: 'Finds opportunities, drafts campaigns, proposes promotions.',
  operations: 'Runs the order lifecycle and watches the stockroom.',
  analytics: 'Turns business data into decisions, not guesses.',
};

const AGENT_DOT: Record<string, string> = {
  manager: 'bg-agent-manager',
  sales: 'bg-agent-sales',
  support: 'bg-agent-support',
  marketing: 'bg-agent-marketing',
  operations: 'bg-agent-operations',
  analytics: 'bg-agent-analytics',
};

export function AgentDot({ type, className = 'w-2.5 h-2.5' }: { type: string; className?: string }) {
  return <span aria-hidden className={`inline-block shrink-0 rounded-full ${className} ${AGENT_DOT[type] || 'bg-ink-faint'}`} />;
}

/** Page header: a docket that names the sheet on the desk. */
export function Docket({ title, memo, action }: { title: string; memo?: string; action?: React.ReactNode }) {
  return (
    <div className='flex items-end justify-between gap-4 flex-wrap mb-7'>
      <div>
        <p className='kicker mb-1.5'>METIS · {memo || 'operations desk'}</p>
        <h1 className='font-display text-3xl sm:text-4xl font-bold tracking-tight text-ink'>{title}</h1>
      </div>
      {action}
    </div>
  );
}

export function LoadingState({ label = 'pulling the day’s records…' }: { label?: string }) {
  return (
    <div className='ledger p-10 text-center'>
      <p className='font-mono text-xs uppercase tracking-[0.16em] text-ink-soft'>{label}</p>
    </div>
  );
}

export function EmptyState({ title, note }: { title: string; note: string }) {
  return (
    <div className='ledger p-10 text-center'>
      <p className='font-display text-xl font-semibold text-ink'>{title}</p>
      <p className='font-mono text-xs uppercase tracking-[0.12em] text-ink-faint mt-2'>{note}</p>
    </div>
  );
}

/** A rubber stamp. Use --slam to slam it down once. */
export function Stamp({
  text,
  tone = 'ok',
  slam = false,
  className = '',
  small = false,
}: {
  text: string;
  tone?: 'ok' | 'danger';
  slam?: boolean;
  className?: string;
  small?: boolean;
}) {
  return (
    <span
      aria-hidden
      className={`stamp ${tone === 'ok' ? 'stamp--ok' : 'stamp--danger'} ${slam ? 'stamp--slam' : ''} ${small ? 'stamp--small' : ''} ${className}`}
    >
      {text}
    </span>
  );
}

export function RiskTicket({ level }: { level: string }) {
  const tone = level === 'low' ? 'ticket--ok' : level === 'high' ? 'ticket--danger' : 'ticket--warn';
  return (
    <span className={`ticket ${tone}`}>
      {level} risk
    </span>
  );
}

export function StatusTicket({ status }: { status: string }) {
  const tone = status === 'completed' ? 'ticket--ok' : status === 'failed' ? 'ticket--danger' : status === 'pending' ? 'ticket--warn' : 'ticket--carbon';
  return <span className={`ticket ${tone}`}>{status}</span>;
}

export function Cash({ value, className = '' }: { value: number; className?: string }) {
  return (
    <span className={`tabular ${className}`}>
      ৳{Math.round(value).toLocaleString()}
    </span>
  );
}

export function DateTime({ value, date = false }: { value: string; date?: boolean }) {
  try {
    if (date) {
      return (
        <time dateTime={value} className='tabular'>
          {new Date(value).toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' })}
        </time>
      );
    }
    return (
      <time dateTime={value} className='tabular'>
        {new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </time>
    );
  } catch {
    return <span>{value}</span>;
  }
}