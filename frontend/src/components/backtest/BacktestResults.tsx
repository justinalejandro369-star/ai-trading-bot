import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { runBacktest } from '@/api/backtest'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import EquityCurveChart from '@/components/chart/EquityCurveChart'
import type { BacktestResult } from '@/types'

const INTERVALS = ['1D', '4H', '1H']

export default function BacktestResults() {
  const [symbol, setSymbol] = useState('AAPL')
  const [interval, setInterval] = useState('1D')

  const { mutate, isPending, data: result, error } = useMutation<
    BacktestResult,
    Error,
    { symbol: string; interval: string; initial_cash: number; commission: number; slippage_pct: number }
  >({
    mutationFn: runBacktest,
  })

  const handleRun = () => {
    mutate({ symbol, interval, initial_cash: 10000, commission: 0.001, slippage_pct: 0.001 })
  }

  // Map equity_curve to EquityCurveChart's expected shape
  const equityCurveData = result?.equity_curve.map((pt) => ({
    recorded_at: new Date(pt.time * 1000).toISOString(),
    equity: pt.equity,
  })) ?? []

  return (
    <div data-testid="backtest-results" className="space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <h2 className="text-lg font-semibold text-slate-100">Backtest Strategy</h2>
      </div>

      {/* Controls */}
      <div className="flex items-end gap-3 flex-wrap">
        <div className="space-y-1">
          <label className="text-xs text-slate-400">Symbol</label>
          <Input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="w-28 bg-slate-800 border-slate-600 text-slate-100"
            placeholder="AAPL"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-400">Interval</label>
          <select
            value={interval}
            onChange={(e) => setInterval(e.target.value)}
            className="bg-slate-800 border border-slate-600 text-slate-100 text-sm rounded px-2 py-2 h-9 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {INTERVALS.map((i) => (
              <option key={i} value={i}>{i}</option>
            ))}
          </select>
        </div>
        <Button
          onClick={handleRun}
          disabled={isPending}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          {isPending ? 'Running...' : 'Run Backtest'}
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-400 rounded-lg px-4 py-3 text-sm">
          {error.message}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div
            data-testid="backtest-metrics"
            className="grid grid-cols-2 sm:grid-cols-4 gap-4"
          >
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-4">
                <div className="text-xs text-slate-500 mb-1">Sharpe Ratio</div>
                <div className="text-xl font-bold text-slate-100">
                  {result.sharpe_ratio.toFixed(2)}
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-4">
                <div className="text-xs text-slate-500 mb-1">Max Drawdown</div>
                <div className="text-xl font-bold text-red-400">
                  {(result.max_drawdown * 100).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-4">
                <div className="text-xs text-slate-500 mb-1">Win Rate</div>
                <div className="text-xl font-bold text-emerald-400">
                  {(result.win_rate * 100).toFixed(1)}%
                </div>
              </CardContent>
            </Card>
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-4">
                <div className="text-xs text-slate-500 mb-1">Profit Factor</div>
                <div className="text-xl font-bold text-slate-100">
                  {result.profit_factor.toFixed(2)}
                </div>
              </CardContent>
            </Card>
          </div>

          <div data-testid="backtest-equity-chart">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">Equity Curve</h3>
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-3">
              <EquityCurveChart data={equityCurveData} />
            </div>
          </div>
        </div>
      )}

      {!result && !isPending && (
        <div className="flex items-center justify-center h-40 bg-slate-800 rounded-lg border border-slate-700">
          <p className="text-slate-400 text-sm">
            Select a symbol and interval, then click Run Backtest
          </p>
        </div>
      )}
    </div>
  )
}
