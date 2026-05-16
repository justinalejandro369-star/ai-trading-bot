import { apiGet, apiPost } from '@/api/client'
import type { BacktestResult, BacktestRunSummary, BacktestRunDetail } from '@/types'

export async function runBacktest(params: {
  symbol: string
  interval: string
  initial_cash: number
  commission: number
  slippage_pct: number
  strategy_name?: string
}): Promise<BacktestResult> {
  return apiPost<BacktestResult>('/api/backtest', {
    symbol: params.symbol,
    interval: params.interval,
    init_cash: params.initial_cash,
    commission: params.commission,
    slippage: params.slippage_pct,
    strategy_name: params.strategy_name ?? 'baseline',
  })
}

export async function getBacktestRuns(
  symbol?: string,
  strategy?: string,
): Promise<BacktestRunSummary[]> {
  const params = new URLSearchParams()
  if (symbol) params.set('symbol', symbol)
  if (strategy) params.set('strategy', strategy)
  const qs = params.toString()
  return apiGet<BacktestRunSummary[]>(`/api/backtest/runs${qs ? `?${qs}` : ''}`)
}

export async function getBacktestRun(id: number): Promise<BacktestRunDetail> {
  return apiGet<BacktestRunDetail>(`/api/backtest/runs/${id}`)
}
