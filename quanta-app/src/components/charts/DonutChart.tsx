import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import ChartTooltip from './ChartTooltip'

interface DonutData {
  label: string
  value: number
  color: string
}

interface DonutChartProps {
  data: DonutData[]
  height?: number
}

export default function DonutChart({ data, height = 200 }: DonutChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  )
}
