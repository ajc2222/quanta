'use client'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import ChartTooltip from '../components/charts/ChartTooltip'

// putOi values are negative to extend left (population pyramid style)
const oiData = [
  { strike: '5,650', callOi: 12450, putOi: -18200 },
  { strike: '5,675', callOi: 15800, putOi: -22100 },
  { strike: '5,700', callOi: 21200, putOi: -28400 },
  { strike: '5,710', callOi: 18400, putOi: -16200 },
  { strike: '5,720', callOi: 14200, putOi: -12100 },
  { strike: '5,730', callOi: 9800, putOi: -8400 },
  { strike: '5,740', callOi: 11200, putOi: -9600 },
  { strike: '5,750', callOi: 15200, putOi: -13800 },
  { strike: '5,760', callOi: 18600, putOi: -15400 },
  { strike: '5,770', callOi: 22400, putOi: -18200 },
  { strike: '5,780', callOi: 26800, putOi: -21200 },
  { strike: '5,790', callOi: 21400, putOi: -16800 },
  { strike: '5,800', callOi: 18200, putOi: -14200 },
  { strike: '5,810', callOi: 15800, putOi: -12400 },
  { strike: '5,820', callOi: 13400, putOi: -10200 },
  { strike: '5,830', callOi: 16800, putOi: -11800 },
  { strike: '5,840', callOi: 19200, putOi: -13800 },
  { strike: '5,850', callOi: 22400, putOi: -16200 },
  { strike: '5,860', callOi: 18600, putOi: -12800 },
  { strike: '5,875', callOi: 14200, putOi: -9600 },
  { strike: '5,900', callOi: 9800, putOi: -7200 },
  { strike: '5,925', callOi: 6200, putOi: -5400 },
]

const maxOi = Math.max(
  ...oiData.map((d) => Math.max(Math.abs(d.callOi), Math.abs(d.putOi))),
)

export default function OIByStrike() {
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-[18px] font-semibold text-text-highlight font-sans">OI by Strike</h1>

      <div className="bg-surface border border-border p-4">
        <ResponsiveContainer width="100%" height={560}>
          <BarChart
            data={oiData}
            layout="vertical"
            barCategoryGap={3}
            margin={{ top: 8, right: 16, bottom: 8, left: 16 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" horizontal={false} />
            <XAxis
              type="number"
              tickFormatter={(v: number) => `${Math.abs(v / 1000)}k`}
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              domain={[-maxOi * 1.15, maxOi * 1.15]}
            />
            <YAxis
              type="category"
              dataKey="strike"
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={60}
              reversed
            />
            <Tooltip
              content={<ChartTooltip />}
              cursor={{ fill: '#1E1E2E', opacity: 0.3 }}
            />
            <ReferenceLine x={0} stroke="#1E1E2E" strokeWidth={1} />
            <ReferenceLine
              y="5,800"
              stroke="#FFFFFF"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              label={{
                value: '● 5,800',
                position: 'insideTopLeft' as const,
                fill: '#FFFFFF',
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            />
            <Bar
              dataKey="putOi"
              fill="#EF4444"
              radius={[0, 3, 3, 0]}
              stackId="a"
            />
            <Bar
              dataKey="callOi"
              fill="#22C55E"
              radius={[3, 0, 0, 3]}
              stackId="a"
            />
          </BarChart>
        </ResponsiveContainer>

        <div className="flex items-center justify-center gap-6 mt-3">
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-3 h-3 bg-red" /> Put OI
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-3 h-3 bg-green" /> Call OI
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted font-sans">
            <span className="inline-block w-3 h-0.5 bg-text-highlight" style={{ width: 14 }} /> Current Price
          </span>
        </div>
      </div>
    </div>
  )
}
