import type { Metadata } from 'next'
import './globals.css'
import { StoreHydrator } from '@/components/StoreHydrator'
import { Toaster } from 'react-hot-toast'

export const metadata: Metadata = {
  title: 'HackerScan Pro',
  description: 'Enterprise Security Scanning Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <StoreHydrator />
        <Toaster position="bottom-right" toastOptions={{
          style: {
            background: '#111',
            color: '#fff',
            border: '1px solid #333',
            fontFamily: 'monospace',
            fontSize: '12px'
          }
        }} />
        {children}
      </body>
    </html>
  )
}
