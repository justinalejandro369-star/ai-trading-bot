import { useQuery } from '@tanstack/react-query'
import { getTopSignals } from '@/api/signals'
import { Badge } from '@/components/ui/badge'
import type { Signal } from '@/types'
import SignalCard from './SignalCard'

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
