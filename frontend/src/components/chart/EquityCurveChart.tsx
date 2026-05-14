import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { useChartColors } from '@/hooks/useChartColors'
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
  const colors = useChartColors()

  return (
    <ResponsiveContainer data-testid="equity-curve-chart" width="100%" height={250}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
        <XAxis
          dataKey="recorded_at"
          tickFormatter={fmtDate}
          tick={{ fill: colors.text, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={['auto', 'auto']}
          tick={{ fill: colors.text, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={70}
          tickFormatter={(v: number) => `$${v.toLocaleString()}`}
        />
        <Tooltip
          contentStyle={{ backgroundColor: colors.tooltipBg, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 6 }}
          labelStyle={{ color: colors.text }}
          itemStyle={{ color: colors.green }}
          formatter={(v: unknown) => [`$${(v as number).toLocaleString()}`, 'Equity']}
          labelFormatter={(label: unknown) => fmtDate(label as string)}
        />
        <Line
          type="monotone"
          dataKey="equity"
          stroke={colors.green}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
