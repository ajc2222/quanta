'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { NAV_SECTIONS } from '../../constants'
import type { NavItem } from '../../types'

interface SidebarProps {
  onSoonClick?: () => void
}

export default function Sidebar({ onSoonClick }: SidebarProps) {
  return (
    <aside className="w-60 h-screen fixed left-0 top-0 bg-[#0A0A0F] border-r border-[#1E1E2E] flex flex-col z-50 select-none">
      {/* Logo */}
      <div className="px-5 pt-6 pb-4">
        <span className="text-text-highlight text-lg tracking-[0.15em] font-semibold font-sans">
          QUANTA
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto">
        {NAV_SECTIONS.map((section) => {
          const hasSoonItems = section.items.some((i) => i.badge === 'soon')
          return (
            <div key={section.label}>
              <div className="flex items-center gap-2 px-5 pt-6 pb-2">
                <span className="text-[10px] text-muted uppercase tracking-wider font-medium">
                  {section.label}
                </span>
                {hasSoonItems && (
                  <span className="text-[9px] bg-amber text-black px-1.5 py-0.5 rounded font-semibold leading-none">
                    SOON
                  </span>
                )}
              </div>
              {section.items.map((item) => (
                <NavItemComponent
                  key={item.id}
                  item={item}
                  onSoonClick={onSoonClick}
                />
              ))}
            </div>
          )
        })}
      </nav>

      {/* Bottom: user info */}
      <div className="px-5 py-4 border-t border-border flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-bg-surface flex items-center justify-center text-xs text-muted font-medium shrink-0">
          AJ
        </div>
        <div className="flex-1 min-w-0 text-xs text-muted truncate">
          aidancady15@gmail.com
        </div>
        <button
          className="shrink-0 text-muted hover:text-text-primary transition-colors duration-100"
          aria-label="Settings"
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>
    </aside>
  )
}

/* ─── Nav Item ─────────────────────────────────────────────────── */

function NavItemComponent({
  item,
  onSoonClick,
}: {
  item: NavItem
  onSoonClick?: () => void
}) {
  const pathname = usePathname()
  const isSoon = item.badge === 'soon'
  const isActive = pathname === item.path

  if (isSoon) {
    return (
      <button
        onClick={onSoonClick}
        className="w-full flex items-center justify-between px-5 py-2.5 text-sm font-medium text-text-primary opacity-40 cursor-pointer text-left transition-colors duration-100"
      >
        <span>{item.label}</span>
      </button>
    )
  }

  return (
    <Link
      href={item.path}
      className={`flex items-center px-5 py-2.5 text-sm font-medium transition-colors duration-100 ${
        isActive
          ? 'border-l-[3px] border-accent text-accent bg-bg-surface'
          : 'text-text-primary hover:bg-bg-surface border-l-[3px] border-transparent'
      }`}
    >
      {item.label}
    </Link>
  )
}
