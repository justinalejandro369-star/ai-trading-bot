import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Tooltip,
  Legend,
  Cell,
} from 'recharts'
import { useChartColors } from '@/hooks/useChartColors'
import type { PaperPosition } from '@/types'

const COLORS = ['#44E092', '#5D8BFF', '#FFB3AD', '#FF5451', '#B2C5FF', '#03C177']

interface Props {
  positions: PaperPosition[]
}

export default function PnLPieChart({ positions }: Props) {
  const colors = useChartColors()
  const totalValue = positions.reduce((sum, p) => sum + p.quantity * p.avg_entry_price, 0)
  const chartData = positions.map((p) => ({
    symbol: p.symbol,
    value: p.quantity * p.avg_entry_price,
    pct: totalValue > 0 ? ((p.quantity * p.avg_entry_price) / totalValue) * 100 : 0,
  }))

  if (chartData.length === 0) {
    return (
      <div
        data-testid="allocation-pie-chart"
        className="flex items-center justify-center h-[200px] text-muted-foreground text-sm"
      >
        No positions
      </div>
    )
  }

  return (
    <ResponsiveContainer data-testid="allocation-pie-chart" width="100%" height={200}>
      <PieChart>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="symbol"
          cx="50%"
          cy="50%"
          outerRadius={70}
        >
          {chartData.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ backgroundColor: colors.tooltipBg, border: `1px solid ${colors.tooltipBorder}`, borderRadius: 6 }}
          formatter={(val: unknown, name: unknown) => {
            const v = val as number
            const n = name as string
            return [`$${v.toLocaleString()} (${chartData.find((d) => d.symbol === n)?.pct.toFixed(1)}%)`, n]
          }}
        />
        <Legend
          formatter={(val) => <span style={{ color: colors.legendText, fontSize: 12 }}>{val}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
