import { useSearchParams } from 'react-router-dom'
import { useCallback } from 'react'
import {
  INSTRUMENTS,
  LOOKBACK_OPTIONS,
  SESSION_OPTIONS,
  DEFAULT_FILTERS,
} from '../../constants'
import type { ReportFilterState } from '../../types'

interface FilterBarProps {
  /** Optional extra filter label rendered after standard filters */
  reportFilter?: string
  /** Called whenever any filter changes */
  onChange?: (state: ReportFilterState) => void
}

const LOOKBACK_VALUES = LOOKBACK_OPTIONS.map((o) => o.value)

export default function FilterBar({ reportFilter, onChange }: FilterBarProps) {
  const [searchParams, setSearchParams] = useSearchParams()

  /* ── Derive current state from URL ──────────────────────────── */

  const instruments: string[] =
    searchParams
      .get('instruments')
      ?.split(',')
      .filter((s) => INSTRUMENTS.includes(s)) ?? DEFAULT_FILTERS.instruments

  const lookback = LOOKBACK_VALUES.includes(
    searchParams.get('lookback') as (typeof LOOKBACK_VALUES)[number],
  )
    ? (searchParams.get('lookback') as ReportFilterState['lookback'])
    : DEFAULT_FILTERS.lookback

  const session = SESSION_OPTIONS.includes(searchParams.get('session') ?? '')
    ? (searchParams.get('session') as string)
    : DEFAULT_FILTERS.session

  /* ── Update helpers ─────────────────────────────────────────── */

  const update = useCallback(
    (patch: Partial<ReportFilterState>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if ('instruments' in patch) {
            if (
              !patch.instruments ||
              patch.instruments.length === 0 ||
              patch.instruments.join(',') === DEFAULT_FILTERS.instruments.join(',')
            ) {
              next.delete('instruments')
            } else {
              next.set('instruments', patch.instruments.join(','))
            }
          }
          if ('lookback' in patch) {
            if (patch.lookback === DEFAULT_FILTERS.lookback) {
              next.delete('lookback')
            } else {
              next.set('lookback', patch.lookback!)
            }
          }
          if ('session' in patch) {
            if (patch.session === DEFAULT_FILTERS.session) {
              next.delete('session')
            } else {
              next.set('session', patch.session!)
            }
          }
          return next
        },
        { replace: true },
      )
      // notify parent
      const merged: ReportFilterState = {
        instruments: patch.instruments ?? instruments,
        lookback: patch.lookback ?? lookback,
        session: patch.session ?? session,
      }
      onChange?.(merged)
    },
    [instruments, lookback, session, onChange, setSearchParams],
  )

  const toggleInstrument = useCallback(
    (symbol: string) => {
      const next = instruments.includes(symbol)
        ? instruments.filter((s) => s !== symbol)
        : [...instruments, symbol]
      update({ instruments: next.length ? next : [symbol] })
    },
    [instruments, update],
  )

  return (
    <div className="flex items-center flex-wrap gap-3 py-3">
      {/* Instrument pills */}
      <div className="flex items-center gap-1">
        {INSTRUMENTS.map((s) => {
          const active = instruments.includes(s)
          return (
            <button
              key={s}
              onClick={() => toggleInstrument(s)}
              className={`relative px-3 py-1.5 text-sm leading-none rounded border font-mono transition-colors duration-100 ${
                active
                  ? 'border-accent text-accent bg-bg-surface pr-2'
                  : 'border-border text-muted hover:text-text-primary hover:border-border'
              }`}
            >
              <span className={active ? 'mr-1' : ''}>{s}</span>
              {active && (
                <span
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleInstrument(s)
                  }}
                  className="inline-flex items-center justify-center w-3 h-3 text-[10px] leading-none rounded-sm hover:bg-accent/20"
                >
                  &times;
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Lookback segmented buttons */}
      <div className="flex items-center">
        {LOOKBACK_OPTIONS.map((opt, i) => {
          const active = lookback === opt.value
          return (
            <button
              key={opt.value}
              onClick={() => update({ lookback: opt.value })}
              className={`px-3 py-1.5 text-sm leading-none border border-border font-mono transition-colors duration-100 ${
                i === 0 ? 'rounded-l' : ''
              } ${i === LOOKBACK_OPTIONS.length - 1 ? 'rounded-r' : ''} ${
                active
                  ? 'bg-accent text-text-highlight border-accent'
                  : 'bg-transparent text-muted hover:text-text-primary'
              }`}
            >
              {opt.label}
            </button>
          )
        })}
      </div>

      {/* Session dropdown */}
      <select
        value={session}
        onChange={(e) => update({ session: e.target.value })}
        className="bg-bg-surface text-text-primary border border-border rounded px-3 py-1.5 text-sm leading-none font-mono outline-none cursor-pointer transition-colors duration-100 focus:border-accent"
      >
        {SESSION_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {/* Optional report-specific filter placeholder */}
      {reportFilter && (
        <span className="text-muted text-xs ml-auto">{reportFilter}</span>
      )}
    </div>
  )
}
