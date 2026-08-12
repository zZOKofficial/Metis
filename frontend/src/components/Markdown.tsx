'use client';

import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

const components: Components = {
  p: ({ children }) => <p className='my-2 last:mb-0 leading-relaxed'>{children}</p>,
  h1: ({ children }) => <h1 className='font-display text-lg font-bold mt-4 mb-2'>{children}</h1>,
  h2: ({ children }) => <h2 className='font-display text-base font-bold mt-4 mb-2'>{children}</h2>,
  h3: ({ children }) => <h3 className='font-display text-[15px] font-bold mt-3 mb-1.5'>{children}</h3>,
  h4: ({ children }) => <h4 className='font-display text-sm font-bold mt-3 mb-1.5'>{children}</h4>,
  h5: ({ children }) => <h5 className='font-display text-sm font-bold mt-3 mb-1.5'>{children}</h5>,
  h6: ({ children }) => <h6 className='font-display text-sm font-bold mt-3 mb-1.5'>{children}</h6>,
  ul: ({ children }) => <ul className='list-disc pl-5 my-2 space-y-1'>{children}</ul>,
  ol: ({ children }) => <ol className='list-decimal pl-5 my-2 space-y-1'>{children}</ol>,
  li: ({ children }) => <li className='pl-1'>{children}</li>,
  a: ({ children, href }) => (
    <a className='text-carbon underline underline-offset-2 hover:text-carbon-deep' href={href} target='_blank' rel='noopener noreferrer'>
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className='border-l-2 border-carbon pl-3 my-2 text-ink-soft italic'>{children}</blockquote>
  ),
  hr: () => <hr className='my-4 border-ink/20' />,
  strong: ({ children }) => <strong className='font-semibold'>{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  del: ({ children }) => <del className='line-through'>{children}</del>,
  code: ({ className, children }) => {
    const isBlock = /language-/.test(className || '');
    if (isBlock) {
      return <code className='block text-xs font-mono'>{children}</code>;
    }
    return <code className='bg-ink/10 text-ink-deep rounded-none px-1.5 py-0.5 text-xs font-mono'>{children}</code>;
  },
  pre: ({ children }) => (
    <pre className='bg-ink text-card rounded-none p-4 my-3 overflow-x-auto text-xs font-mono whitespace-pre border-l-[3px] border-l-carbon'>
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className='my-2 overflow-x-auto'>
      <table className='text-sm border-collapse w-full'>{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className='border-b-2 border-ink'>{children}</thead>
  ),
  th: ({ children }) => <th className='border-b border-ink/30 px-2 py-1.5 text-left font-semibold font-mono text-[11px] uppercase tracking-[0.1em]'>{children}</th>,
  td: ({ children }) => <td className='border-b border-[var(--rule)] px-2 py-1.5'>{children}</td>,
};

export default function Markdown({ content }: { content: string }) {
  return (
    <div className='text-[15px] text-ink [&_*:first-child]:mt-0 [&_*:last-child]:mb-0'>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}