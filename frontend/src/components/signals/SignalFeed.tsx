import { useQuery } from '@tanstack/react-query'
import { getTopSignals } from '@/api/signals'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { Signal } from '@/types'

function directionClass(direction: string) {
  if (direction === 'BUY') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
  if (direction === 'SELL') return 'bg-red-500/20 text-red-400 border-red-500/40'
  return 'bg-slate-500/20 text-slate-400 border-slate-500/40'
}

function fmt(val: number | null, prefix = '$') {
  if (val === null) return '—'
  return `${prefix}${val.toFixed(2)}`
}

function SignalCard({ signal }: { signal: Signal }) {
  return (
    <Card
      data-testid={`signal-${signal.symbol.toLowerCase()}`}
      className="bg-slate-800 border-slate-700"
    >
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${directionClass(signal.direction)}`}
          >
            {signal.direction}
          </span>
          <span className="font-bold text-slate-100">{signal.symbol}</span>
          <span className="text-xs text-slate-500 italic ml-auto">{signal.regime}</span>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs text-slate-400">
            <span>Confidence</span>
            <span>{signal.confidence}%</span>
          </div>
          <div className="h-1.5 w-full rounded bg-slate-700">
            <div
              className="h-1.5 rounded bg-emerald-500"
              style={{ width: `${signal.confidence}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <div className="text-slate-500">Entry</div>
            <div className="text-slate-200">{fmt(signal.entry_price)}</div>
          </div>
          <div>
            <div className="text-slate-500">Stop-Loss</div>
            <div className="text-red-400">{fmt(signal.stop_loss)}</div>
          </div>
          <div>
            <div className="text-slate-500">Target</div>
            <div className="text-emerald-400">{fmt(signal.target_price)}</div>
          </div>
        </div>

        {signal.reasons.slice(0, 2).length > 0 && (
          <ul className="text-xs text-slate-500 space-y-0.5">
            {signal.reasons.slice(0, 2).map((r, i) => (
              <li key={i}>• {r}</li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

export default function SignalFeed() {
  const { data: signals = [], isLoading } = useQuery<Signal[]>({
    queryKey: ['signals', 'top'],
    queryFn: () => getTopSignals(10),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-slate-100">AI Signal Feed</h2>
        <Badge variant="secondary" className="bg-slate-700 text-slate-300">
          {signals.length}
        </Badge>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-32 rounded-lg bg-slate-800 border border-slate-700 animate-pulse"
            />
          ))}
        </div>
      )}

      {!isLoading && signals.length === 0 && (
        <div className="flex items-center justify-center h-40 bg-slate-800 rounded-lg border border-slate-700">
          <p className="text-slate-400 text-sm">
            No signals yet — scanner runs every 5 minutes
          </p>
        </div>
      )}

      {!isLoading && signals.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {signals.map((signal) => (
            <SignalCard key={`${signal.symbol}-${signal.scanned_at}`} signal={signal} />
          ))}
        </div>
      )}
    </div>
  )
}
