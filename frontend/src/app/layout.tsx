import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'METIS — Your Business. Operated by AI.',
  description: 'An AI workforce of specialized agents that runs sales, support, marketing, operations and analytics for small businesses.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en'>
      <head>
        <link rel='preconnect' href='https://fonts.googleapis.com' />
        <link rel='preconnect' href='https://fonts.gstatic.com' crossOrigin='anonymous' />
        <link
          href='https://fonts.googleapis.com/css2?family=Archivo:ital,wght@0,400;0,500;0,600;0,700;1,500&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&display=swap'
          rel='stylesheet'
        />
        <meta name='theme-color' content='#201d17' />
      </head>
      <body>{children}</body>
    </html>
  );
}