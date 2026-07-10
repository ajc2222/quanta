import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { ChartBar } from '../../types'
import ChartTooltip from './ChartTooltip'

interface BarChartProps {
  data: ChartBar[]
  height?: number
  color?: string
  barBg?: string
  layout?: 'horizontal' | 'vertical'
}

export default function BarChart({
  data,
  height = 260,
  color = '#4F6EF7',
  barBg = '#111118',
  layout = 'horizontal',
}: BarChartProps) {
  const isVertical = layout === 'vertical'
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsBarChart data={data} layout={layout} barCategoryGap="20%" margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" vertical={false} />
        {isVertical ? (
          <>
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={60}
            />
          </>
        ) : (
          <>
            <XAxis
              dataKey="label"
              type="category"
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="number"
              tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={0}
            />
          </>
        )}
        <Tooltip content={<ChartTooltip />} cursor={{ fill: '#1E1E2E', opacity: 0.3 }} />
        <Bar dataKey="value" background={{ fill: barBg }} radius={[0, 0, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color || color} />
          ))}
        </Bar>
      </RechartsBarChart>
    </ResponsiveContainer>
  )
}
