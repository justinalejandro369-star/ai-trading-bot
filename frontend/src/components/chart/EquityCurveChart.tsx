import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import type { EquityPoint } from '@/types'

interface Props {
  data: EquityPoint[]
}

function fmtDate(val: string) {
  try {
    return new Date(val).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return val
  }
}

export default function EquityCurveChart({ data }: Props) {
  return (
    <ResponsiveContainer data-testid="equity-curve-chart" width="100%" height={250}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="recorded_at"
          tickFormatter={fmtDate}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={['auto', 'auto']}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={70}
          tickFormatter={(v: number) => `$${v.toLocaleString()}`}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 6 }}
          labelStyle={{ color: '#94a3b8' }}
          itemStyle={{ color: '#10b981' }}
          formatter={(v: unknown) => [`$${(v as number).toLocaleString()}`, 'Equity']}
          labelFormatter={(label: unknown) => fmtDate(label as string)}
        />
        <Line
          type="monotone"
          dataKey="equity"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
