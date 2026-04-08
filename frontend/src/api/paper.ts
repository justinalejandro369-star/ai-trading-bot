import { apiGet } from '@/api/client'
import type { PaperAccount, EquityPoint } from '@/types'

export async function getAccount(id: number): Promise<PaperAccount> {
  return apiGet<PaperAccount>(`/api/paper/accounts/${id}`)
}

export async function getEquityCurve(id: number): Promise<EquityPoint[]> {
  const res = await apiGet<{ account_id: number; equity_curve: [string, number][] }>(
    `/api/paper/accounts/${id}/equity`
  )
  return res.equity_curve.map(([recorded_at, equity]) => ({ recorded_at, equity }))
}

export async function getCompare(id: number): Promise<Record<string, number>> {
  return apiGet<Record<string, number>>(`/api/paper/accounts/${id}/compare`)
}
