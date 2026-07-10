import { useState } from 'react'
import BarChart from '../components/charts/BarChart'
import StatCard from '../components/reports/StatCard'
import DataTable from '../components/reports/DataTable'
import type { ChartBar } from '../types'

const MACRO_WINDOWS = ['9:50-10:10', '10:50-11:10', '1:10-1:40', '2:10-2:40', '3:15-4:00']

const hodMacro: ChartBar[] = [
  { label: '9:50', value: 4 }, { label: '9:55', value: 9 },
  { label: '10:00', value: 14 }, { label: '10:05', value: 11 },
  { label: '10:10', value: 6 },
]

const lodMacro: ChartBar[] = [
  { label: '9:50', value: 7 }, { label: '9:55', value: 12 },
  { label: '10:00', value: 10 }, { label: '10:05', value: 8 },
  { label: '10:10', value: 5 },
]

const contRevData: ChartBar[] = [
  { label: 'Continuation', value: 63, color: '#22C55E' },
  { label: 'Reversal', value: 37, color: '#EF4444' },
]

const tableColumns = [
  { key: 'situation', label: 'Situation' },
  { key: 'bullish', label: 'Bullish %', align: 'right' as const, renderBar: true },
  { key: 'bearish', label: 'Bearish %', align: 'right' as const, renderBar: true },
  { key: 'choppy', label: 'Choppy %', align: 'right' as const, renderBar: true },
  { key: 'samples', label: 'n', align: 'right' as const },
  { key: 'avgMag', label: 'Avg Mag', align: 'right' as const },
]

const tableRows = [
  { situation: 'HOD made · Bull PO3 · 8:30 news', bullish: 72, bearish: 18, choppy: 10, samples: 47, avgMag: 32.4 },
  { situation: 'LOD made · Bear PO3 · 8:30 news', bullish: 14, bearish: 76, choppy: 10, samples: 41, avgMag: 34.1 },
  { situation: 'HOD made · Bull PO3 · No news', bullish: 65, bearish: 22, choppy: 13, samples: 83, avgMag: 28.6 },
  { situation: 'LOD made · Bear PO3 · No news', bullish: 20, bearish: 68, choppy: 12, samples: 76, avgMag: 26.2 },
  { situation: 'No HOD/LOD · Bull PO3', bullish: 48, bearish: 32, choppy: 20, samples: 55, avgMag: 18.4 },
  { situation: 'No HOD/LOD · Bear PO3', bullish: 30, bearish: 50, choppy: 20, samples: 52, avgMag: 17.9 },
  { situation: 'Inside FVG · 10:00 news', bullish: 44, bearish: 36, choppy: 20, samples: 28, avgMag: 22.3 },
  { situation: 'At OB · No news', bullish: 38, bearish: 42, choppy: 20, samples: 34, avgMag: 20.1 },
]

interface PillBtnProps {
  active: boolean
  label: string
  onClick: () => void
}

function PillBtn({ active, label, onClick }: PillBtnProps) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 text-[12px] font-sans transition-colors ${
        active ? 'bg-accent text-text-highlight' : 'text-muted hover:text-text-primary border border-border'
      }`}
    >
      {label}
    </button>
  )
}

export default function Macros() {
  const [window, setWindow] = useState('9:50-10:10')
  const [filtersOpen, setFiltersOpen] = useState(false)

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-[18px] font-semibold text-text-highlight font-sans">Macros</h1>

      {/* Window selector */}
      <div className="flex items-center gap-1 flex-wrap">
        {MACRO_WINDOWS.map((w) => (
          <PillBtn key={w} active={window === w} label={w} onClick={() => setWindow(w)} />
        ))}
      </div>

      {/* Prior Context Filters */}
      <div className="border border-border">
        <button
          onClick={() => setFiltersOpen(!filtersOpen)}
          className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] text-muted font-sans uppercase tracking-wider hover:text-text-primary transition-colors"
        >
          <span className={`transition-transform ${filtersOpen ? 'rotate-90' : ''}`}>{'>'}</span>
          Prior Context Filters
        </button>
        {filtersOpen && (
          <div className="px-3 pb-3 pt-2 border-t border-border grid grid-cols-3 gap-x-4 gap-y-2">
            {[
              { label: 'HOD/LOD Made', options: ['Any', 'HOD made', 'LOD made', 'Neither'] },
              { label: 'Preceding PO3 Phase', options: ['Any', 'Bullish', 'Bearish', 'Ambiguous'] },
              { label: 'Approaching PD Array', options: ['Any', 'Inside FVG', 'At OB', 'None'] },
              { label: 'News Present', options: ['Any', '8:30 news', '10:00 news', 'None'] },
              { label: 'NY Open Direction', options: ['Any', 'Bullish', 'Bearish'] },
              { label: 'London Direction', options: ['Any', 'Bullish', 'Bearish'] },
            ].map((field) => (
              <div key={field.label} className="flex items-center gap-2">
                <span className="text-[11px] text-muted font-sans whitespace-nowrap">{field.label}:</span>
                <select className="bg-bg-surface border border-border text-[12px] text-text-primary px-2 py-1 font-sans flex-1 min-w-0">
                  {field.options.map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Row 1: Stat cards */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="Bullish %" value="58.2%" secondary="n=403" />
        <StatCard label="Bearish %" value="32.7%" secondary="n=403" />
        <StatCard label="Choppy %" value="9.1%" secondary="n=403" />
        <StatCard label="Avg Magnitude" value="24.8" secondary="ES points" />
        <StatCard label="Sample Size" value="403" status="healthy" />
      </div>

      {/* Row 2: Twin histograms */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">HOD TIME DISTRIBUTION</h3>
          <BarChart data={hodMacro} height={180} color="#22C55E" />
        </div>
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">LOD TIME DISTRIBUTION</h3>
          <BarChart data={lodMacro} height={180} color="#EF4444" />
        </div>
      </div>

      {/* Row 3: Continuation vs Reversal */}
      <div className="bg-surface border border-border p-4">
        <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">CONTINUATION vs REVERSAL</h3>
        <div className="flex items-center gap-8">
          <div className="w-64">
            <BarChart data={contRevData} height={120} color="#22C55E" />
          </div>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <span className="inline-block w-3 h-3 bg-green" />
              <span className="text-[13px] text-text-primary font-sans">Continuation: <span className="font-mono text-green">63%</span></span>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-block w-3 h-3 bg-red" />
              <span className="text-[13px] text-text-primary font-sans">Reversal: <span className="font-mono text-red">37%</span></span>
            </div>
            <div className="text-[11px] text-muted font-sans mt-1">Based on {window} window · n=403</div>
          </div>
        </div>
      </div>

      {/* Row 4: Data table */}
      <div className="bg-surface border border-border p-4">
        <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">SITUATIONAL COMBO STATS</h3>
        <DataTable columns={tableColumns} rows={tableRows} />
      </div>
    </div>
  )
}
