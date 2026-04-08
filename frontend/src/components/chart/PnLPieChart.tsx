import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Tooltip,
  Legend,
  Cell,
} from 'recharts'
import type { PaperPosition } from '@/types'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

interface Props {
  positions: PaperPosition[]
}

export default function PnLPieChart({ positions }: Props) {
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
        className="flex items-center justify-center h-[200px] text-slate-500 text-sm"
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
          contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 6 }}
          formatter={(val: unknown, name: unknown) => {
            const v = val as number
            const n = name as string
            return [`$${v.toLocaleString()} (${chartData.find((d) => d.symbol === n)?.pct.toFixed(1)}%)`, n]
          }}
        />
        <Legend
          formatter={(val) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{val}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
