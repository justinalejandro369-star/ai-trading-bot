import { apiGet } from '@/api/client'
import type { Candle } from '@/types'

export async function getCandles(
  symbol: string,
  interval = '1D',
  limit = 200,
): Promise<Candle[]> {
  const data = await apiGet<Candle[]>(
    `/api/market-data/${symbol}?interval=${interval}&limit=${limit}`,
  )
  return [...data].reverse() // Backend returns DESC; chart requires ASC
}

export async function getIndicators(symbol: string): Promise<Record<string, number>> {
  return apiGet<Record<string, number>>(`/api/indicators/${symbol}`)
}
