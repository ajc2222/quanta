'use client'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts'
import ChartTooltip from '../components/charts/ChartTooltip'
import StatCard from '../components/reports/StatCard'

const gexLevelCards = [
  { label: 'Call Wall', value: '5,875', secondary: 'Resistance' },
  { label: 'Put Wall', value: '5,700', secondary: 'Support' },
  { label: 'GEX Flip', value: '5,800', secondary: 'Regime flip' },
  { label: 'Zero Gamma', value: '5,780', secondary: 'Neutral zone' },
  { label: 'Max Pain', value: '5,750', secondary: 'Options pain' },
]

const gexData = [
  { strike: '5,650', gex: -1.2 },
  { strike: '5,675', gex: -2.8 },
  { strike: '5,700', gex: -4.5 },
  { strike: '5,710', gex: -3.1 },
  { strike: '5,720', gex: -1.8 },
  { strike: '5,730', gex: -0.5 },
  { strike: '5,740', gex: 0.3 },
  { strike: '5,750', gex: 1.2 },
  { strike: '5,760', gex: 2.1 },
  { strike: '5,770', gex: 3.5 },
  { strike: '5,780', gex: 5.8 },
  { strike: '5,790', gex: 4.2 },
  { strike: '5,800', gex: 2.8 },
  { strike: '5,810', gex: 1.5 },
  { strike: '5,820', gex: 0.8 },
  { strike: '5,830', gex: 1.2 },
  { strike: '5,840', gex: 2.5 },
  { strike: '5,850', gex: 4.8 },
  { strike: '5,860', gex: 6.2 },
  { strike: '5,875', gex: 8.5 },
  { strike: '5,900', gex: 6.1 },
  { strike: '5,925', gex: 3.4 },
]

export default function GEXLevels() {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="text-[18px] font-semibold text-text-highlight font-sans">GEX Levels</h1>
        <span className="text-[11px] text-muted font-mono">Last updated: 14:32 ET · refreshes every 30m</span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-3">
        {gexLevelCards.map((c) => (
          <StatCard key={c.label} label={c.label} value={c.value} secondary={c.secondary} />
        ))}
      </div>

      {/* GEX Profile Chart */}
      <div className="bg-surface border border-border p-4">
        <h3 className="text-[11px] font-semibold text-text-primary font-sans uppercase tracking-wider mb-3">GEX PROFILE</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={gexData} barCategoryGap={4} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" vertical={false} />
            <XAxis
              dataKey="strike"
              tick={{ fontSize: 10, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              interval={2}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: '#1E1E2E', opacity: 0.3 }} />
            <ReferenceLine y={0} stroke="#1E1E2E" strokeWidth={1} />
            <ReferenceLine
              x="5,800"
              stroke="#FFFFFF"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: '5,800 ▼',
                position: 'top',
                fill: '#FFFFFF',
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            />
            <Bar dataKey="gex" radius={[0, 0, 0, 0]}>
              {gexData.map((entry, i) => (
                <Cell key={i} fill={entry.gex >= 0 ? '#22C55E' : '#EF4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-4 mt-2">
          <span className="flex items-center gap-1 text-[10px] text-muted font-sans">
            <span className="inline-block w-2 h-2 bg-green" /> Call GEX
          </span>
          <span className="flex items-center gap-1 text-[10px] text-muted font-sans">
            <span className="inline-block w-2 h-2 bg-red" /> Put GEX
          </span>
          <span className="flex items-center gap-1 text-[10px] text-muted font-sans">
            <span className="inline-block w-2 h-0.5 bg-text-highlight" style={{ width: 12, borderTop: '1px dashed #FFFFFF' }} /> Current Price
          </span>
        </div>
      </div>
    </div>
  )
}
