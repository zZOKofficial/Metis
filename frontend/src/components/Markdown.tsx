'use client';

import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

const components: Components = {
  p: ({ children }) => <p className='my-1.5 last:mb-0'>{children}</p>,
  h1: ({ children }) => <h1 className='text-lg font-bold mt-3 mb-1.5'>{children}</h1>,
  h2: ({ children }) => <h2 className='text-base font-bold mt-3 mb-1.5'>{children}</h2>,
  h3: ({ children }) => <h3 className='text-sm font-semibold mt-2 mb-1'>{children}</h3>,
  h4: ({ children }) => <h4 className='text-sm font-semibold mt-2 mb-1'>{children}</h4>,
  h5: ({ children }) => <h5 className='text-sm font-semibold mt-2 mb-1'>{children}</h5>,
  h6: ({ children }) => <h6 className='text-sm font-semibold mt-2 mb-1'>{children}</h6>,
  ul: ({ children }) => <ul className='list-disc pl-5 my-1.5 space-y-0.5'>{children}</ul>,
  ol: ({ children }) => <ol className='list-decimal pl-5 my-1.5 space-y-0.5'>{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  a: ({ children, href }) => (
    <a className='text-metis-600 underline hover:text-metis-700' href={href} target='_blank' rel='noopener noreferrer'>
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className='border-l-4 border-metis-200 pl-3 my-2 text-slate-500 italic'>{children}</blockquote>
  ),
  hr: () => <hr className='my-3 border-slate-200' />,
  strong: ({ children }) => <strong className='font-semibold'>{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  del: ({ children }) => <del className='line-through'>{children}</del>,
  code: ({ className, children }) => {
    const isBlock = /language-/.test(className || '');
    if (isBlock) {
      return <code className='block text-xs font-mono'>{children}</code>;
    }
    return <code className='bg-slate-200 text-slate-800 rounded px-1 py-0.5 text-xs font-mono'>{children}</code>;
  },
  pre: ({ children }) => (
    <pre className='bg-slate-800 text-slate-100 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono whitespace-pre'>{children}</pre>
  ),
  table: ({ children }) => (
    <div className='my-2 overflow-x-auto'>
      <table className='text-sm border-collapse'>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className='bg-slate-200'>{children}</thead>,
  th: ({ children }) => <th className='border border-slate-300 px-2 py-1 text-left font-semibold'>{children}</th>,
  td: ({ children }) => <td className='border border-slate-300 px-2 py-1'>{children}</td>,
};

export default function Markdown({ content }: { content: string }) {
  return (
    <div className='text-sm text-slate-800 [&_*:first-child]:mt-0 [&_*:last-child]:mb-0'>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
