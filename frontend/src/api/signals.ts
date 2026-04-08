import { apiGet } from '@/api/client'
import type { Signal } from '@/types'

export async function getTopSignals(limit = 10): Promise<Signal[]> {
  return apiGet<Signal[]>(`/api/signals/top?limit=${limit}`)
}
