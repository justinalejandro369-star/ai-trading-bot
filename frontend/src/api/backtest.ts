import { apiPost } from '@/api/client'
import type { BacktestResult } from '@/types'

export async function runBacktest(params: {
  symbol: string
  interval: string
  initial_cash: number
  commission: number
  slippage_pct: number
}): Promise<BacktestResult> {
  return apiPost<BacktestResult>('/api/backtest', params)
}
