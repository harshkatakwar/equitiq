import type { Metadata } from 'next';
import './globals.css';
import { Providers } from '@/components/providers';
import { Navbar } from '@/components/navbar';

const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'ResearchOS';

export const metadata: Metadata = {
  title: `${APP_NAME} — Indian Equity Research`,
  description: 'Search companies, view financials, track earnings, and leverage AI-powered research with verified citations.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen">
        <Providers>
          <Navbar />
          <main className="pt-16">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
