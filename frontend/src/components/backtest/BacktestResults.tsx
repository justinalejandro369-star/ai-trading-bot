import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { runBacktest } from '@/api/backtest'
import { getStrategies } from '@/api/strategies'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import EquityCurveChart from '@/components/chart/EquityCurveChart'
import type { BacktestResult, Strategy } from '@/types'

const INTERVALS = ['1D', '4H', '1H']

export default function BacktestResults() {
  const [symbol, setSymbol] = useState('AAPL')
  const [interval, setInterval] = useState('1D')
  const [strategyName, setStrategyName] = useState('baseline')

  const { data: strategies = [] } = useQuery<Strategy[]>({
    queryKey: ['strategies'],
    queryFn: getStrategies,
    staleTime: 5 * 60_000,
  })

  const { mutate, isPending, data: result, error } = useMutation<
    BacktestResult,
    Error,
    { symbol: string; interval: string; initial_cash: number; commission: number; slippage_pct: number; strategy_name: string }
  >({
    mutationFn: runBacktest,
  })

  const handleRun = () => {
    mutate({
      symbol,
      interval,
      initial_cash: 10000,
      commission: 0.001,
      slippage_pct: 0.001,
      strategy_name: strategyName,
    })
  }

  // Backend returns equity_curve as [[iso_string, value], ...] tuples
  const equityCurveData = (result?.equity_curve as unknown as [string, number][] ?? []).map(
    ([ts, equity]) => ({ recorded_at: ts, equity })
  )

  return (
    <div data-testid="backtest-results" className="space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <h2 className="text-lg font-semibold text-[var(--kt-on-surface)]">Backtest Strategy</h2>
      </div>

      {/* Controls */}
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
          <label className="label-terminal text-[var(--kt-on-surface-variant)]">Strategy</label>
          <select
            data-testid="strategy-select"
            value={strategyName}
            onChange={(e) => setStrategyName(e.target.value)}
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
          disabled={isPending}
          className="bg-gradient-to-r from-[var(--kt-primary-container)] to-[var(--kt-secondary-container)] text-white hover:opacity-90"
        >
          {isPending ? 'Running...' : 'Run Backtest'}
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-[var(--kt-tertiary-container)]/20 text-[var(--kt-tertiary)] rounded-lg px-4 py-3 text-sm">
          {error.message}
        </div>
      )}

      {/* Results — metric cards use tonal background shift, no borders */}
      {result && (
        <div className="space-y-4">
          <div
            data-testid="backtest-metrics"
            className="grid grid-cols-2 sm:grid-cols-4 gap-4"
          >
            <Card className="bg-[var(--kt-surface-container-low)] border-none">
              <CardContent className="pt-4">
                <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1">Sharpe Ratio</div>
                <div className="text-xl font-bold font-mono text-[var(--kt-on-surface)]">
                  {result.sharpe_ratio.toFixed(2)}
                </div>
              </CardContent>
            </Card>
            <Card className="bg-[var(--kt-surface-container-low)] border-none">
              <CardContent className="pt-4">
                <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1">Max Drawdown</div>
                <div className="text-xl font-bold font-mono text-[var(--kt-tertiary-container)]">
                  {(result.max_drawdown * 100).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
            <Card className="bg-[var(--kt-surface-container-low)] border-none">
              <CardContent className="pt-4">
                <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1">Win Rate</div>
                <div className="text-xl font-bold font-mono text-[var(--kt-secondary)]">
                  {(result.win_rate * 100).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
            <Card className="bg-[var(--kt-surface-container-low)] border-none">
              <CardContent className="pt-4">
                <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1">Profit Factor</div>
                <div className="text-xl font-bold font-mono text-[var(--kt-on-surface)]">
                  {result.profit_factor.toFixed(2)}
                </div>
              </CardContent>
            </Card>
          </div>

          <div data-testid="backtest-equity-chart">
            <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">Equity Curve</h3>
            <div className="bg-[var(--kt-surface-container-low)] rounded-lg p-3">
              <EquityCurveChart data={equityCurveData} />
            </div>
          </div>
        </div>
      )}

      {!result && !isPending && (
        <div className="flex items-center justify-center h-40 bg-[var(--kt-surface-container-low)] rounded-lg">
          <p className="text-[var(--kt-on-surface-variant)] text-sm">
            Select a symbol and interval, then click Run Backtest
          </p>
        </div>
      )}
    </div>
  )
}
