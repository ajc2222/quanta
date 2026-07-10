import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from 'recharts'
import ChartTooltip from '../components/charts/ChartTooltip'

const pcData = [
  { label: 'Jun 9', ratio: 0.85, avg20: 0.82 },
  { label: 'Jun 10', ratio: 0.92, avg20: 0.83 },
  { label: 'Jun 11', ratio: 0.78, avg20: 0.82 },
  { label: 'Jun 12', ratio: 0.88, avg20: 0.83 },
  { label: 'Jun 13', ratio: 0.95, avg20: 0.84 },
  { label: 'Jun 16', ratio: 0.82, avg20: 0.83 },
  { label: 'Jun 17', ratio: 0.76, avg20: 0.83 },
  { label: 'Jun 18', ratio: 0.91, avg20: 0.83 },
  { label: 'Jun 19', ratio: 1.02, avg20: 0.84 },
  { label: 'Jun 20', ratio: 0.88, avg20: 0.84 },
  { label: 'Jun 23', ratio: 0.79, avg20: 0.83 },
  { label: 'Jun 24', ratio: 0.84, avg20: 0.83 },
  { label: 'Jun 25', ratio: 0.97, avg20: 0.84 },
  { label: 'Jun 26', ratio: 1.08, avg20: 0.85 },
  { label: 'Jun 27', ratio: 0.86, avg20: 0.84 },
  { label: 'Jun 30', ratio: 0.81, avg20: 0.84 },
  { label: 'Jul 1', ratio: 0.74, avg20: 0.83 },
  { label: 'Jul 2', ratio: 0.93, avg20: 0.84 },
  { label: 'Jul 3', ratio: 0.87, avg20: 0.84 },
  { label: 'Jul 7', ratio: 0.96, avg20: 0.84 },
  { label: 'Jul 8', ratio: 1.12, avg20: 0.85 },
  { label: 'Jul 9', ratio: 0.89, avg20: 0.85 },
]

// ponytail: hardcoded y-axis padding, compute from data if values drift outside [0.5, 1.4]
const yMin = 0.5
const yMax = 1.4

export default function PutCallRatio() {
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-[18px] font-semibold text-text-highlight font-sans">Put/Call Ratio</h1>

      <div className="bg-surface border border-border p-4">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={pcData} margin={{ top: 16, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 10, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              interval={2}
            />
            <YAxis
              domain={[yMin, yMax]}
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#1E1E2E', strokeWidth: 1 }} />

            {/* Overbought / oversold bands */}
            <ReferenceArea y1={1.1} y2={yMax} fill="#EF4444" fillOpacity={0.06} />
            <ReferenceArea y1={yMin} y2={0.65} fill="#22C55E" fillOpacity={0.06} />
            <ReferenceArea y1={0.65} y2={0.75} fill="#F59E0B" fillOpacity={0.04} />

            {/* Reference lines */}
            <ReferenceLine y={1.0} stroke="#1E1E2E" strokeWidth={1} strokeDasharray="2 2" />
            <ReferenceLine y={0.65} stroke="#EF4444" strokeWidth={1} strokeDasharray="3 3" />
            <ReferenceLine y={1.1} stroke="#22C55E" strokeWidth={1} strokeDasharray="3 3" />

            <Line
              type="monotone"
              dataKey="ratio"
              stroke="#FFFFFF"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#FFFFFF' }}
            />
            <Line
              type="monotone"
              dataKey="avg20"
              stroke="#4F6EF7"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#4F6EF7' }}
            />
          </LineChart>
        </ResponsiveContainer>

        <div className="flex items-center justify-center gap-6 mt-3">
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-4 h-0.5 bg-text-highlight" /> Daily P/C Ratio
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-4 h-0.5 bg-accent" /> 20-day MA
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-2 h-2 rounded-sm bg-red opacity-30" /> Overbought
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-2 h-2 rounded-sm bg-green opacity-30" /> Oversold
          </span>
        </div>
      </div>
    </div>
  )
}
