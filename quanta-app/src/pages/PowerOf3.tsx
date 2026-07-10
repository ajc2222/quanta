import { useState } from 'react'
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import BarChart from '../components/charts/BarChart'
import DonutChart from '../components/charts/DonutChart'
import ChartTooltip from '../components/charts/ChartTooltip'
import StatCard from '../components/reports/StatCard'
import type { ChartBar } from '../types'

const WINDOWS = ['Daily', '4H·6AM', '4H·10AM', '30m·9:30', '30m·10:00', 'NY Session', '15m·9:45']
const PHASES = ['All', 'Bullish', 'Bearish', 'Ambiguous']

const hodTimeData: ChartBar[] = [
  { label: '9:30', value: 3 }, { label: '9:45', value: 8 },
  { label: '10:00', value: 14 }, { label: '10:15', value: 22 },
  { label: '10:30', value: 18 }, { label: '10:45', value: 12 },
  { label: '11:00', value: 9 }, { label: '11:15', value: 6 },
  { label: '11:30', value: 4 }, { label: '11:45', value: 5 },
  { label: '12:00', value: 7 }, { label: '12:15', value: 10 },
  { label: '12:30', value: 8 }, { label: '12:45', value: 6 },
  { label: '13:00', value: 5 }, { label: '13:15', value: 9 },
  { label: '13:30', value: 11 }, { label: '13:45', value: 7 },
  { label: '14:00', value: 4 }, { label: '14:15', value: 3 },
  { label: '14:30', value: 2 }, { label: '14:45', value: 2 },
  { label: '15:00', value: 1 }, { label: '15:45', value: 1 },
]

const lodTimeData: ChartBar[] = hodTimeData.map(d => ({ ...d, value: Math.round(d.value * (0.5 + Math.random() * 0.8)) }))

const avgRangeData: ChartBar[] = [
  { label: 'Mon', value: 24.5 }, { label: 'Tue', value: 28.1 },
  { label: 'Wed', value: 22.3 }, { label: 'Thu', value: 26.7 },
  { label: 'Fri', value: 19.8 },
]

const pdArrayHod = [
  { label: 'FVG', value: 35, color: '#4F6EF7' },
  { label: 'OB', value: 25, color: '#22C55E' },
  { label: 'Key Open', value: 18, color: '#F59E0B' },
  { label: 'Round #', value: 12, color: '#6B7280' },
  { label: 'None', value: 10, color: '#EF4444' },
]

const pdArrayLod = [
  { label: 'FVG', value: 28, color: '#4F6EF7' },
  { label: 'OB', value: 22, color: '#22C55E' },
  { label: 'Key Open', value: 20, color: '#F59E0B' },
  { label: 'Round #', value: 18, color: '#6B7280' },
  { label: 'None', value: 12, color: '#EF4444' },
]

const manipDepth: ChartBar[] = [
  { label: '0-25%', value: 18 }, { label: '25-50%', value: 34 },
  { label: '50-75%', value: 28 }, { label: '75-100%', value: 14 },
  { label: '100%+', value: 6 },
]

const phaseRateWeekday = [
  { label: 'Mon', bullish: 42, bearish: 33, ambiguous: 25 },
  { label: 'Tue', bullish: 38, bearish: 35, ambiguous: 27 },
  { label: 'Wed', bullish: 45, bearish: 30, ambiguous: 25 },
  { label: 'Thu', bullish: 35, bearish: 38, ambiguous: 27 },
  { label: 'Fri', bullish: 40, bearish: 32, ambiguous: 28 },
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

export default function PowerOf3() {
  const [window, setWindow] = useState('Daily')
  const [phase, setPhase] = useState('All')
  const [htfOpen, setHtfOpen] = useState(false)

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-[18px] font-semibold text-text-highlight font-sans">Power of 3</h1>

      {/* Window selector */}
      <div className="flex items-center gap-1 flex-wrap">
        {WINDOWS.map((w) => (
          <PillBtn key={w} active={window === w} label={w} onClick={() => setWindow(w)} />
        ))}
      </div>

      {/* Phase filter */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-muted font-sans uppercase tracking-wider">Phase:</span>
        <div className="flex items-center gap-1">
          {PHASES.map((p) => (
            <PillBtn key={p} active={phase === p} label={p} onClick={() => setPhase(p)} />
          ))}
        </div>
      </div>

      {/* HTF Context Filter */}
      <div className="border border-border">
        <button
          onClick={() => setHtfOpen(!htfOpen)}
          className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] text-muted font-sans uppercase tracking-wider hover:text-text-primary transition-colors"
        >
          <span className={`transition-transform ${htfOpen ? 'rotate-90' : ''}`}>{'>'}</span>
          HTF Context Filter
        </button>
        {htfOpen && (
          <div className="px-3 pb-3 pt-1 border-t border-border flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-muted font-sans">Daily PO3 Phase</span>
              <select className="bg-bg-surface border border-border text-[12px] text-text-primary px-2 py-1 font-sans">
                <option>Any</option><option>Bullish</option><option>Bearish</option>
              </select>
            </div>
            <span className="text-muted text-[11px]">→</span>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-muted font-sans">4H Phase</span>
              <select className="bg-bg-surface border border-border text-[12px] text-text-primary px-2 py-1 font-sans">
                <option>Any</option><option>Bullish</option><option>Bearish</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="Win Rate" value="68.4%" secondary="n=403" status="healthy" />
        <StatCard label="Avg Range" value="24.8" secondary="ES points" />
        <StatCard label="Avg HOD Time" value="11:24" secondary="ET" />
        <StatCard label="Avg LOD Time" value="10:42" secondary="ET" />
      </div>

      {/* 2x2 grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* HOD Time Distribution */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">HOD TIME DISTRIBUTION</h3>
          <BarChart data={hodTimeData} height={200} color="#22C55E" />
        </div>
        {/* LOD Time Distribution */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">LOD TIME DISTRIBUTION</h3>
          <BarChart data={lodTimeData} height={200} color="#EF4444" />
        </div>
        {/* Avg Range by Weekday */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">AVG RANGE BY WEEKDAY</h3>
          <BarChart data={avgRangeData} height={200} color="#4F6EF7" layout="vertical" />
        </div>
        {/* News Day vs Non-News */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">NEWS DAY vs NON-NEWS</h3>
          <div className="grid grid-cols-2 gap-4 h-[200px]">
            <div className="border border-border p-3 flex flex-col justify-between">
              <span className="text-[10px] uppercase tracking-wider text-muted font-sans">News Day</span>
              <div>
                <div className="text-[11px] text-muted font-sans mb-1">Avg Range</div>
                <span className="text-[24px] font-bold text-text-highlight font-mono">26.4</span>
              </div>
              <div className="text-[11px] text-muted font-sans">Bullish 52% · Bearish 48%</div>
            </div>
            <div className="border border-border p-3 flex flex-col justify-between">
              <span className="text-[10px] uppercase tracking-wider text-muted font-sans">Non-News</span>
              <div>
                <div className="text-[11px] text-muted font-sans mb-1">Avg Range</div>
                <span className="text-[24px] font-bold text-text-highlight font-mono">22.1</span>
              </div>
              <div className="text-[11px] text-muted font-sans">Bullish 47% · Bearish 53%</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-4 gap-4">
        {/* PD Array Held HOD */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-2">PD ARRAY HELD HOD</h3>
          <DonutChart data={pdArrayHod} height={200} />
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
            {pdArrayHod.map((d) => (
              <span key={d.label} className="flex items-center gap-1 text-[10px] text-muted font-sans">
                <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                {d.label} {Math.round((d.value / pdArrayHod.reduce((s, x) => s + x.value, 0)) * 100)}%
              </span>
            ))}
          </div>
        </div>
        {/* PD Array Held LOD */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-2">PD ARRAY HELD LOD</h3>
          <DonutChart data={pdArrayLod} height={200} />
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
            {pdArrayLod.map((d) => (
              <span key={d.label} className="flex items-center gap-1 text-[10px] text-muted font-sans">
                <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                {d.label} {Math.round((d.value / pdArrayLod.reduce((s, x) => s + x.value, 0)) * 100)}%
              </span>
            ))}
          </div>
        </div>
        {/* Manipulation Depth */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">MANIPULATION DEPTH</h3>
          <BarChart data={manipDepth} height={200} color="#4F6EF7" />
        </div>
        {/* Phase Rates by Weekday */}
        <div className="bg-surface border border-border p-4">
          <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">PHASE RATES BY WEEKDAY</h3>
          <ResponsiveContainer width="100%" height={200}>
            <RechartsBarChart data={phaseRateWeekday} barCategoryGap="20%" margin={{ top: 8, right: 4, bottom: 8, left: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }} axisLine={false} tickLine={false} width={30} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: '#1E1E2E', opacity: 0.3 }} />
              <Bar dataKey="bullish" stackId="a" fill="#22C55E" radius={[0, 0, 0, 0]} />
              <Bar dataKey="bearish" stackId="a" fill="#EF4444" />
              <Bar dataKey="ambiguous" stackId="a" fill="#F59E0B" radius={[0, 0, 0, 0]} />
            </RechartsBarChart>
          </ResponsiveContainer>
          <div className="flex items-center gap-3 mt-2">
            <span className="flex items-center gap-1 text-[10px] text-muted font-sans"><span className="inline-block w-2 h-2 bg-green" /> Bullish</span>
            <span className="flex items-center gap-1 text-[10px] text-muted font-sans"><span className="inline-block w-2 h-2 bg-red" /> Bearish</span>
            <span className="flex items-center gap-1 text-[10px] text-muted font-sans"><span className="inline-block w-2 h-2 bg-amber" /> Ambiguous</span>
          </div>
        </div>
      </div>
    </div>
  )
}
