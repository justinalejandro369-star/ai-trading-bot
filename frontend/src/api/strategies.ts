import { apiGet } from '@/api/client'
import type { Strategy } from '@/types'

export async function getStrategies(): Promise<Strategy[]> {
  return apiGet<Strategy[]>('/api/strategies')
}

export async function getStrategy(name: string): Promise<Strategy> {
  return apiGet<Strategy>(`/api/strategies/${encodeURIComponent(name)}`)
}
