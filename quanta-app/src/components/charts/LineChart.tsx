import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import ChartTooltip from './ChartTooltip'

interface LineConfig {
  key: string
  color: string
}

interface LineChartProps {
  data: Record<string, string | number>[]
  lines: LineConfig[]
  height?: number
}

export default function LineChart({ data, lines, height = 260 }: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#1E1E2E', strokeWidth: 1 }} />
        {lines.map((line) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            stroke={line.color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: line.color }}
          />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  )
}
