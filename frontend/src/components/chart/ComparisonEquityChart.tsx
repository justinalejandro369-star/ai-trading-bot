import { useState } from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { Button } from '@/components/ui/button'
import { useChartColors } from '@/hooks/useChartColors'

export interface ComparisonPoint {
  date: string
  backtest: number | null
  live: number | null
}

interface Props {
  data: ComparisonPoint[]
}

function fmtDate(val: string) {
  try {
    return new Date(val).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return val
  }
}

export default function ComparisonEquityChart({ data }: Props) {
  const [logScale, setLogScale] = useState(false)
  const colors = useChartColors()

  // Export both curves as CSV for user download
  const handleExportCsv = () => {
    const header = 'Date,Backtest,Live\n'
    const rows = data
      .map((d) => `${d.date},${d.backtest ?? ''},${d.live ?? ''}`)
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'equity-comparison.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setLogScale((v) => !v)}
          className="text-xs"
        >
          {logScale ? 'Linear Scale' : 'Log Scale'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExportCsv}
          className="text-xs"
        >
          Export CSV
        </Button>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} />
          <XAxis
            dataKey="date"
            tickFormatter={fmtDate}
            tick={{ fill: colors.text, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={['auto', 'auto']}
            scale={logScale ? 'log' : 'auto'}
            tick={{ fill: colors.text, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={(v: number) => `$${v.toLocaleString()}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.tooltipBg,
              border: `1px solid ${colors.tooltipBorder}`,
              borderRadius: 6,
            }}
            labelStyle={{ color: colors.text }}
            formatter={(v: unknown, name: unknown) => [
              `$${(v as number).toLocaleString()}`,
              name as string,
            ]}
            labelFormatter={(label: unknown) => fmtDate(label as string)}
          />
          <Legend
            formatter={(val) => (
              <span style={{ color: colors.legendText, fontSize: 12 }}>{val}</span>
            )}
          />
          {/* Backtest projection: dashed blue line */}
          <Line
            type="monotone"
            dataKey="backtest"
            name="Backtest Projection"
            stroke={colors.blue}
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            connectNulls
          />
          {/* Live execution: solid green line */}
          <Line
            type="monotone"
            dataKey="live"
            name="Live Execution"
            stroke={colors.green}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
