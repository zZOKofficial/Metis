/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        paper: '#F4EFE3',
        card: '#FCFAF3',
        ink: {
          DEFAULT: '#201D17',
          soft: '#6E675A',
          faint: '#9B9484',
        },
        carbon: {
          DEFAULT: '#2E5E9E',
          deep: '#21476F',
        },
        stamp: {
          DEFAULT: '#B03A2E',
          deep: '#8E2D24',
        },
        ok: {
          DEFAULT: '#3F7049',
          deep: '#2E5535',
        },
        agent: {
          manager: '#2E5E9E',
          sales: '#3F7049',
          support: '#7A5A9C',
          marketing: '#B07A2E',
          operations: '#2F7A74',
          analytics: '#9A6A48',
        },
      },
      fontFamily: {
        display: ['var(--font-display)', 'Georgia', 'serif'],
        body: ['var(--font-body)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'Menlo', 'monospace'],
      },
      boxShadow: {
        print: '2.5px 2.5px 0 0 rgba(32,29,23,0.85)',
        'print-sm': '1.5px 1.5px 0 0 rgba(32,29,23,0.85)',
        'print-lg': '4px 4px 0 0 rgba(32,29,23,0.8)',
      },
      transitionTimingFunction: {
        'stamp-bounce': 'cubic-bezier(0.2, 0.7, 0.3, 1.4)',
      },
    },
  },
  plugins: [],
};