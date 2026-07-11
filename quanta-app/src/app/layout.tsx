import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import '@/index.css'

export const metadata: Metadata = {
  title: 'Quanta',
  description: 'Trading analytics platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}
