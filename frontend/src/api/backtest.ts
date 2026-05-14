import { apiGet, apiPost } from '@/api/client'
import type { BacktestResult, BacktestRunSummary, BacktestRunDetail } from '@/types'

export async function runBacktest(params: {
  symbol: string
  interval: string
  initial_cash: number
  commission: number
  slippage_pct: number
}): Promise<BacktestResult> {
  return apiPost<BacktestResult>('/api/backtest', {
    symbol: params.symbol,
    interval: params.interval,
    init_cash: params.initial_cash,
    commission: params.commission,
    slippage: params.slippage_pct,
  })
}

export async function getBacktestRuns(symbol?: string): Promise<BacktestRunSummary[]> {
  const path = symbol ? `/api/backtest/runs?symbol=${encodeURIComponent(symbol)}` : '/api/backtest/runs'
  return apiGet<BacktestRunSummary[]>(path)
}

export async function getBacktestRun(id: number): Promise<BacktestRunDetail> {
  return apiGet<BacktestRunDetail>(`/api/backtest/runs/${id}`)
}
