import type { Metadata } from 'next'
import './globals.css'
import { StoreHydrator } from '@/components/StoreHydrator'

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
        {children}
      </body>
    </html>
  )
}
