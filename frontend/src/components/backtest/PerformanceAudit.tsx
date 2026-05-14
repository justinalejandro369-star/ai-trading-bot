import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getBacktestRuns, getBacktestRun } from '@/api/backtest'
import { getEquityCurve } from '@/api/paper'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import ComparisonEquityChart from '@/components/chart/ComparisonEquityChart'
import type { ComparisonPoint } from '@/components/chart/ComparisonEquityChart'
import type { BacktestRunSummary, EquityPoint } from '@/types'

const ACCOUNT_ID = 1

// Threshold for "significant" variance between backtest and live equity (5%)
const VARIANCE_THRESHOLD = 0.05

interface DegradationEntry {
  date: string
  expected: number
  actual: number
  variancePct: number
  attribution: string
  risk: 'Critical' | 'Minor' | 'Negligible'
}

// Classify risk based on how far live performance diverges from backtest
function classifyRisk(variancePct: number): DegradationEntry['risk'] {
  const abs = Math.abs(variancePct)
  if (abs >= 10) return 'Critical'
  if (abs >= 5) return 'Minor'
  return 'Negligible'
}

// Guess attribution reason based on the direction and magnitude of variance
function guessAttribution(variancePct: number): string {
  if (variancePct < -10) return 'Slippage / Execution Gap'
  if (variancePct < -5) return 'Market Regime Shift'
  if (variancePct > 5) return 'Favorable Execution'
  return 'Normal Variance'
}

export default function PerformanceAudit() {
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)

  // Fetch list of historical backtest runs
  const { data: runs = [], isLoading: loadingRuns } = useQuery<BacktestRunSummary[]>({
    queryKey: ['backtest-runs'],
    queryFn: () => getBacktestRuns(),
    staleTime: 60_000,
  })

  // Auto-select the first run when data loads
  const activeRunId = selectedRunId ?? (runs.length > 0 ? runs[0].id : null)

  // Fetch full detail (with equity_curve) for the selected run
  const { data: runDetail } = useQuery({
    queryKey: ['backtest-run', activeRunId],
    queryFn: () => getBacktestRun(activeRunId!),
    enabled: activeRunId !== null,
    staleTime: 120_000,
  })

  // Fetch live paper-trading equity curve for comparison
  const { data: liveEquity = [] } = useQuery<EquityPoint[]>({
    queryKey: ['equity', ACCOUNT_ID],
    queryFn: () => getEquityCurve(ACCOUNT_ID),
    staleTime: 30_000,
  })

  // Merge backtest equity curve + live equity into a single timeline for the chart
  const comparisonData: ComparisonPoint[] = useMemo(() => {
    if (!runDetail?.equity_curve) return []

    // Index live equity by date (YYYY-MM-DD) for O(1) lookups
    const liveByDate = new Map<string, number>()
    liveEquity.forEach((pt) => {
      const day = pt.recorded_at.slice(0, 10)
      liveByDate.set(day, pt.equity)
    })

    // Build merged timeline keyed by date
    const merged = new Map<string, ComparisonPoint>()

    // Add backtest points
    for (const [ts, value] of runDetail.equity_curve) {
      const day = ts.slice(0, 10)
      const existing = merged.get(day)
      if (existing) {
        existing.backtest = value
      } else {
        merged.set(day, { date: day, backtest: value, live: liveByDate.get(day) ?? null })
      }
    }

    // Add any live points not already present
    liveEquity.forEach((pt) => {
      const day = pt.recorded_at.slice(0, 10)
      if (!merged.has(day)) {
        merged.set(day, { date: day, backtest: null, live: pt.equity })
      } else {
        merged.get(day)!.live = pt.equity
      }
    })

    return Array.from(merged.values()).sort((a, b) => a.date.localeCompare(b.date))
  }, [runDetail, liveEquity])

  // Compute degradation log: find dates where variance exceeds threshold
  const degradationLog: DegradationEntry[] = useMemo(() => {
    return comparisonData
      .filter((pt) => pt.backtest !== null && pt.live !== null && pt.backtest !== 0)
      .map((pt) => {
        const variancePct = ((pt.live! - pt.backtest!) / Math.abs(pt.backtest!)) * 100
        return {
          date: pt.date,
          expected: pt.backtest!,
          actual: pt.live!,
          variancePct,
          attribution: guessAttribution(variancePct),
          risk: classifyRisk(variancePct),
        }
      })
      .filter((entry) => Math.abs(entry.variancePct) >= VARIANCE_THRESHOLD * 100)
      .slice(0, 20) // Keep the log manageable
  }, [comparisonData])

  // Compute KPI values from the selected run and live equity
  const selectedRun = runs.find((r) => r.id === activeRunId) ?? null
  const backtestROI = selectedRun?.total_return ?? null
  const backtestDD = selectedRun?.max_drawdown ?? null

  // Compute live ROI from paper equity curve
  const liveROI = useMemo(() => {
    if (liveEquity.length < 2) return null
    const first = liveEquity[0].equity
    const last = liveEquity[liveEquity.length - 1].equity
    if (first === 0) return null
    return (last - first) / first
  }, [liveEquity])

  // Compute live max drawdown from paper equity curve
  const liveDD = useMemo(() => {
    if (liveEquity.length === 0) return null
    let peak = -Infinity
    let maxDD = 0
    for (const pt of liveEquity) {
      if (pt.equity > peak) peak = pt.equity
      const dd = (peak - pt.equity) / peak
      if (dd > maxDD) maxDD = dd
    }
    return maxDD
  }, [liveEquity])

  // Variance between backtest and live ROI
  const roiVariance = backtestROI !== null && liveROI !== null ? liveROI - backtestROI : null

  // Excess drawdown: how much worse live DD is compared to backtest DD
  const ddExcess = backtestDD !== null && liveDD !== null ? liveDD - backtestDD : null

  if (loadingRuns) {
    return (
      <div className="flex items-center justify-center h-40 text-[var(--kt-on-surface-variant)] text-sm">
        Loading backtest history...
      </div>
    )
  }

  if (runs.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 bg-[var(--kt-surface-container-low)] rounded-lg">
        <p className="text-[var(--kt-on-surface-variant)] text-sm">
          No backtest runs found. Run a backtest first to compare against live performance.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header + strategy selector */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-lg font-semibold text-[var(--kt-on-surface)]">Performance Audit</h2>
          <p className="text-sm text-[var(--kt-on-surface-variant)]">
            Compare backtest projections against live paper-trading results
          </p>
        </div>
        <div className="space-y-1">
          <label className="label-terminal text-[var(--kt-on-surface-variant)]">Strategy Run</label>
          <select
            value={activeRunId ?? ''}
            onChange={(e) => setSelectedRunId(Number(e.target.value))}
            className="bg-[var(--kt-surface-container-lowest)] border border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] text-sm rounded px-2 py-2 h-9 focus:outline-none focus:ring-1 focus:ring-[var(--kt-primary-container)]"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.symbol} / {r.interval} — {new Date(r.run_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Comparison Grid — No-Line Rule */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Backtest ROI */}
        <Card className="bg-[var(--kt-surface-container-low)] border-none border-l-2 border-l-[var(--kt-primary-container)]/30">
          <CardContent className="pt-4">
            <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1">Backtest ROI</div>
            <div className="text-xl font-bold font-mono text-[var(--kt-on-surface)]">
              {backtestROI !== null ? `${(backtestROI * 100).toFixed(1)}%` : '—'}
            </div>
          </CardContent>
        </Card>

        {/* Live ROI + variance badge */}
        <Card className="bg-[var(--kt-surface-container-low)] border-none border-l-2 border-l-[var(--kt-secondary)]/30">
          <CardContent className="pt-4">
            <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1 flex items-center gap-2">
              Live ROI
              {roiVariance !== null && (
                <Badge
                  variant="secondary"
                  className={roiVariance >= 0 ? 'bg-[#03C177]/20 text-[#44E092]' : 'bg-[#FF5451]/20 text-[#FFB3AD]'}
                >
                  {roiVariance >= 0 ? '+' : ''}{(roiVariance * 100).toFixed(1)}%
                </Badge>
              )}
            </div>
            <div className={`text-xl font-bold font-mono ${liveROI !== null && liveROI >= 0 ? 'text-[var(--kt-secondary)]' : 'text-[var(--kt-tertiary-container)]'}`}>
              {liveROI !== null ? `${(liveROI * 100).toFixed(1)}%` : '—'}
            </div>
          </CardContent>
        </Card>

        {/* Backtest Max DD */}
        <Card className="bg-[var(--kt-surface-container-low)] border-none border-l-2 border-l-[var(--kt-primary-container)]/30">
          <CardContent className="pt-4">
            <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1">Backtest Max DD</div>
            <div className="text-xl font-bold font-mono text-[var(--kt-tertiary-container)]">
              {backtestDD !== null ? `${(backtestDD * 100).toFixed(1)}%` : '—'}
            </div>
          </CardContent>
        </Card>

        {/* Live Max DD + excess badge */}
        <Card className="bg-[var(--kt-surface-container-low)] border-none border-l-2 border-l-[var(--kt-tertiary-container)]/30">
          <CardContent className="pt-4">
            <div className="label-terminal text-[var(--kt-on-surface-variant)] mb-1 flex items-center gap-2">
              Live Max DD
              {ddExcess !== null && ddExcess > 0 && (
                <Badge variant="secondary" className="bg-[#FF5451]/20 text-[#FFB3AD]">
                  +{(ddExcess * 100).toFixed(1)}% excess
                </Badge>
              )}
            </div>
            <div className="text-xl font-bold font-mono text-[var(--kt-tertiary-container)]">
              {liveDD !== null ? `${(liveDD * 100).toFixed(1)}%` : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Equity Curve Comparison Chart */}
      <div>
        <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">Equity Curve Comparison</h3>
        <div className="bg-[var(--kt-surface-container-low)] rounded-lg p-3">
          {comparisonData.length > 0 ? (
            <ComparisonEquityChart data={comparisonData} />
          ) : (
            <div className="flex items-center justify-center h-[300px] text-[var(--kt-on-surface-variant)] text-sm">
              No overlapping data between backtest and live equity
            </div>
          )}
        </div>
      </div>

      {/* Performance Degradation Log */}
      <div>
        <h3 className="label-terminal text-[var(--kt-on-surface-variant)] mb-2">Performance Degradation Log</h3>
        {degradationLog.length === 0 ? (
          <div className="flex items-center justify-center h-20 bg-[var(--kt-surface-container-low)] rounded-lg">
            <p className="text-[var(--kt-on-surface-variant)] text-sm">
              No significant variance detected between backtest and live performance
            </p>
          </div>
        ) : (
          <div className="rounded-lg overflow-hidden bg-[var(--kt-surface-container-lowest)]">
            <Table>
              <TableHeader>
                <TableRow className="border-[rgba(66,70,84,0.15)] hover:bg-transparent bg-[var(--kt-surface-container-high)]">
                  <TableHead className="text-[var(--kt-on-surface-variant)] label-terminal">Date</TableHead>
                  <TableHead className="text-[var(--kt-on-surface-variant)] label-terminal">Expected</TableHead>
                  <TableHead className="text-[var(--kt-on-surface-variant)] label-terminal">Actual</TableHead>
                  <TableHead className="text-[var(--kt-on-surface-variant)] label-terminal">Variance</TableHead>
                  <TableHead className="text-[var(--kt-on-surface-variant)] label-terminal">Attribution</TableHead>
                  <TableHead className="text-[var(--kt-on-surface-variant)] label-terminal">Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {degradationLog.map((entry) => (
                  <TableRow key={entry.date} className="border-[rgba(66,70,84,0.15)]">
                    <TableCell className="text-[var(--kt-on-surface)] font-mono">{entry.date}</TableCell>
                    <TableCell className="text-[var(--kt-on-surface)] font-mono">${entry.expected.toLocaleString()}</TableCell>
                    <TableCell className="text-[var(--kt-on-surface)] font-mono">${entry.actual.toLocaleString()}</TableCell>
                    <TableCell className={`font-mono ${entry.variancePct >= 0 ? 'text-[var(--kt-secondary)]' : 'text-[var(--kt-tertiary-container)]'}`}>
                      {entry.variancePct >= 0 ? '+' : ''}{entry.variancePct.toFixed(1)}%
                    </TableCell>
                    <TableCell className="text-[var(--kt-on-surface-variant)]">{entry.attribution}</TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={
                          entry.risk === 'Critical'
                            ? 'bg-[#FF5451]/20 text-[#FFB3AD]'
                            : entry.risk === 'Minor'
                              ? 'bg-[var(--kt-surface-container-high)] text-[var(--kt-on-surface-variant)]'
                              : 'bg-[var(--kt-surface-container-high)] text-[var(--kt-on-surface-variant)]/60'
                        }
                      >
                        {entry.risk}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  )
}
