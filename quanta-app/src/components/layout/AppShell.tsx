'use client'
import { useState, useCallback } from 'react'
import Sidebar from './Sidebar'

interface AppShellProps {
  children: React.ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const [showSoonToast, setShowSoonToast] = useState(false)

  const handleSoonClick = useCallback(() => {
    setShowSoonToast(true)
  }, [])

  return (
    <div className="flex min-h-screen bg-bg-primary">
      <Sidebar onSoonClick={handleSoonClick} />

      <main className="flex-1 ml-60 pt-6 px-6">
        {showSoonToast && (
          <div className="mb-4 flex items-center gap-2 bg-bg-surface border border-border rounded px-4 py-2.5 text-sm text-text-primary">
            <svg
              className="w-4 h-4 text-amber shrink-0"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span className="flex-1">
              QT Reports coming soon. ICT module is live now.
            </span>
            <button
              onClick={() => setShowSoonToast(false)}
              className="text-muted hover:text-text-primary transition-colors text-lg leading-none"
              aria-label="Dismiss"
            >
              &times;
            </button>
          </div>
        )}

        {children}
      </main>
    </div>
  )
}
