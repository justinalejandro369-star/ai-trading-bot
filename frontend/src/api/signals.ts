import { apiGet } from '@/api/client'
import type { Signal } from '@/types'

export async function getTopSignals(limit = 10, strategy?: string): Promise<Signal[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (strategy) params.set('strategy', strategy)
  return apiGet<Signal[]>(`/api/signals/top?${params.toString()}`)
}

export async function getAllSignals(strategy?: string): Promise<Signal[]> {
  const params = strategy ? `?strategy=${encodeURIComponent(strategy)}` : ''
  return apiGet<Signal[]>(`/api/signals${params}`)
}
