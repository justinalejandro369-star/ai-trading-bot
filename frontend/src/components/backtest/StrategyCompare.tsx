import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
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
import { runBacktest } from '@/api/backtest'
import { getStrategies } from '@/api/strategies'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useChartColors } from '@/hooks/useChartColors'
import type { BacktestResult, Strategy } from '@/types'

const INTERVALS = ['1D', '4H', '1H']

interface ComparePoint {
  date: string
  a: number | null
  b: number | null
}

function buildComparisonSeries(
  a: BacktestResult | undefined,
  b: BacktestResult | undefined,
): ComparePoint[] {
  if (!a && !b) return []
  const map = new Map<string, ComparePoint>()
  for (const [ts, v] of a?.equity_curve ?? []) {
    map.set(ts, { date: ts, a: v, b: null })
  }
  for (const [ts, v] of b?.equity_curve ?? []) {
    const existing = map.get(ts)
    if (existing) existing.b = v
    else map.set(ts, { date: ts, a: null, b: v })
  }
  return Array.from(map.values()).sort((x, y) => x.date.localeCompare(y.date))
}

function fmtDate(val: string) {
  try {
    return new Date(val).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return val
  }
}

function fmtPct(v: number) {
  return `${(v * 100).toFixed(1)}%`
}

interface MetricRowProps {
  label: string
  a: number | undefined
  b: number | undefined
  format?: (v: number) => string
  betterIs?: 'higher' | 'lower'
}

function MetricRow({ label, a, b, format = (v) => v.toFixed(2), betterIs = 'higher' }: MetricRowProps) {
  const winnerIsA =
    a !== undefined && b !== undefined && (betterIs === 'higher' ? a > b : a < b)
  const winnerIsB =
    a !== undefined && b !== undefined && (betterIs === 'higher' ? b > a : b < a)
  return (
    <tr className="border-b border-[rgba(66,70,84,0.15)] last:border-b-0">
      <td className="py-2 text-xs label-terminal text-[var(--kt-on-surface-variant)]">{label}</td>
      <td
        className={`py-2 font-mono text-sm text-right ${winnerIsA ? 'text-[var(--kt-secondary)] font-bold' : 'text-[var(--kt-on-surface)]'}`}
      >
        {a === undefined ? '—' : format(a)}
      </td>
      <td
        className={`py-2 font-mono text-sm text-right ${winnerIsB ? 'text-[var(--kt-secondary)] font-bold' : 'text-[var(--kt-on-surface)]'}`}
      >
        {b === undefined ? '—' : format(b)}
      </td>
    </tr>
  )
}

export default function StrategyCompare() {
  const [symbol, setSymbol] = useState('AAPL')
  const [interval, setInterval] = useState('1D')
  const [strategyA, setStrategyA] = useState('baseline')
  const [strategyB, setStrategyB] = useState('ma_crossover')

  const colors = useChartColors()

  const { data: strategies = [] } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: getStrategies,
    staleTime: 5 * 60_000,
  })

  // Default to first two unique strategies once they load
  useEffect(() => {
    if (strategies.length >= 2 && strategyA === strategyB) {
      const [first, second] = strategies
      setStrategyA(first.name)
      setStrategyB(second.name)
    }
  }, [strategies, strategyA, strategyB])

  const mutationA = useMutation<BacktestResult, Error, { strategy_name: string }>({
    mutationFn: (vars) =>
      runBacktest({
        symbol,
        interval,
        initial_cash: 10000,
        commission: 0.001,
        slippage_pct: 0.001,
        strategy_name: vars.strategy_name,
      }),
  })
  const mutationB = useMutation<BacktestResult, Error, { strategy_name: string }>({
    mutationFn: (vars) =>
      runBacktest({
        symbol,
        interval,
        initial_cash: 10000,
        commission: 0.001,
        slippage_pct: 0.001,
        strategy_name: vars.strategy_name,
      }),
  })

  const handleRun = () => {
    mutationA.mutate({ strategy_name: strategyA })
    mutationB.mutate({ strategy_name: strategyB })
  }

  const isPending = mutationA.isPending || mutationB.isPending
  const error = mutationA.error ?? mutationB.error
  const resultA = mutationA.data
  const resultB = mutationB.data

  const series = useMemo(
    () => buildComparisonSeries(resultA, resultB),
    [resultA, resultB],
  )

  return (
    <div data-testid="strategy-compare" className="space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <h2 className="text-lg font-semibold text-[var(--kt-on-surface)]">
          Compare Strategies
        </h2>
        <p className="text-xs text-[var(--kt-on-surface-variant)]">
          Run two strategies on the same data and overlay their equity curves.
        </p>
      </div>

      <div className="flex items-end gap-3 flex-wrap">
        <div className="space-y-1">
          <label className="label-terminal text-[var(--kt-on-surface-variant)]">Symbol</label>
          <Input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="w-28 bg-[var(--kt-surface-container-lowest)] border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)]"
            placeholder="Symbol"
          />
        </div>
        <div className="space-y-1">
          <label className="label-terminal text-[var(--kt-on-surface-variant)]">Interval</label>
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            className="bg-[var(--kt-surface-container-lowest)] border border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] text-sm rounded px-2 py-2 h-9 focus:outline-none focus:ring-1 focus:ring-[var(--kt-primary-container)]"
          >
            {INTERVALS.map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="label-terminal text-[var(--kt-on-surface-variant)]">Strategy A</label>
          <select
            data-testid="strategy-a-select"
            value={strategyA}
            onChange={(e) => setStrategyA(e.target.value)}
            className="bg-[var(--kt-surface-container-lowest)] border border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] text-sm rounded px-2 py-2 h-9 focus:outline-none focus:ring-1 focus:ring-[var(--kt-primary-container)]"
          >
            {strategies.length === 0 && <option value="baseline">baseline</option>}
            {strategies.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="label-terminal text-[var(--kt-on-surface-variant)]">Strategy B</label>
          <select
            data-testid="strategy-b-select"
            value={strategyB}
            onChange={(e) => setStrategyB(e.target.value)}
            className="bg-[var(--kt-surface-container-lowest)] border border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] text-sm rounded px-2 py-2 h-9 focus:outline-none focus:ring-1 focus:ring-[var(--kt-primary-container)]"
          >
            {strategies.length === 0 && <option value="baseline">baseline</option>}
            {strategies.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <Button
          onClick={handleRun}
          disabled={isPending || strategyA === strategyB}
          className="bg-gradient-to-r from-[var(--kt-primary-container)] to-[var(--kt-secondary-container)] text-white hover:opacity-90"
        >
          {isPending ? 'Running...' : 'Run Comparison'}
        </Button>
        {strategyA === strategyB && (
          <p className="text-xs text-[var(--kt-tertiary-container)]">Pick two different strategies.</p>
        )}
      </div>

      {error && (
        <div className="bg-[var(--kt-tertiary-container)]/20 text-[var(--kt-tertiary)] rounded-lg px-4 py-3 text-sm">
          {error.message}
        </div>
      )}

      {(resultA || resultB) && (
        <div className="space-y-6">
          <Card className="bg-[var(--kt-surface-container-low)] border-none">
            <CardContent className="pt-4">
              <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-3">
                Metrics
              </h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[rgba(66,70,84,0.15)]">
                    <th className="text-left text-xs label-terminal py-2 text-[var(--kt-on-surface-variant)]" />
                    <th
                      data-testid="metric-header-a"
                      className="text-right text-xs label-terminal py-2 text-[var(--kt-on-surface)]"
                    >
                      {resultA?.strategy_name ?? strategyA}
                    </th>
                    <th
                      data-testid="metric-header-b"
                      className="text-right text-xs label-terminal py-2 text-[var(--kt-on-surface)]"
                    >
                      {resultB?.strategy_name ?? strategyB}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <MetricRow label="Sharpe ratio" a={resultA?.sharpe_ratio} b={resultB?.sharpe_ratio} betterIs="higher" />
                  <MetricRow label="Total return" a={resultA?.total_return} b={resultB?.total_return} format={fmtPct} betterIs="higher" />
                  <MetricRow label="Win rate" a={resultA?.win_rate} b={resultB?.win_rate} format={fmtPct} betterIs="higher" />
                  <MetricRow label="Profit factor" a={resultA?.profit_factor} b={resultB?.profit_factor} betterIs="higher" />
                  <MetricRow label="Max drawdown" a={resultA?.max_drawdown} b={resultB?.max_drawdown} format={fmtPct} betterIs="higher" />
                  <MetricRow
                    label="Total trades"
                    a={resultA?.total_trades}
                    b={resultB?.total_trades}
                    format={(v) => v.toFixed(0)}
                    betterIs="higher"
                  />
                </tbody>
              </table>
            </CardContent>
          </Card>

          <div data-testid="strategy-compare-chart">
            <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">
              Equity Curves
            </h3>
            <div className="bg-[var(--kt-surface-container-low)] rounded-lg p-3">
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={series} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
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
                  <Line
                    type="monotone"
                    dataKey="a"
                    name={resultA?.strategy_name ?? strategyA}
                    stroke={colors.blue}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="b"
                    name={resultB?.strategy_name ?? strategyB}
                    stroke={colors.green}
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {!resultA && !resultB && !isPending && (
        <div className="flex items-center justify-center h-40 bg-[var(--kt-surface-container-low)] rounded-lg">
          <p className="text-[var(--kt-on-surface-variant)] text-sm">
            Pick a symbol, two strategies, then Run Comparison.
          </p>
        </div>
      )}
    </div>
  )
}
