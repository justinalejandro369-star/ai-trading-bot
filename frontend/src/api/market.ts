import { apiGet } from '@/api/client'
import type { Candle } from '@/types'

type RawCandle = {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export async function getCandles(
  symbol: string,
  interval = '1D',
  limit = 200,
): Promise<Candle[]> {
  const data = await apiGet<RawCandle[]>(
    `/api/market-data/${symbol}?interval=${interval}&limit=${limit}`,
  )
  // Backend returns DESC; chart requires ASC. Convert ISO timestamp → Unix seconds.
  return [...data].reverse().map((c) => ({
    time: Math.floor(new Date(c.timestamp).getTime() / 1000),
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close,
    volume: c.volume,
  }))
}

export async function getIndicators(symbol: string): Promise<Record<string, number>> {
  return apiGet<Record<string, number>>(`/api/indicators/${symbol}`)
}

export async function getIndicatorSeries(
  symbol: string,
  interval = '1D',
  limit = 200,
): Promise<import('@/types').IndicatorSeries> {
  return apiGet(`/api/indicator-series/${symbol}?interval=${interval}&limit=${limit}`)
}

export async function getChartAnalysis(
  symbol: string,
  interval = '1D',
  pivotMethod = 'standard',
): Promise<import('@/types').ChartAnalysis> {
  return apiGet(`/api/chart-analysis/${symbol}?interval=${interval}&pivot_method=${pivotMethod}`)
}
