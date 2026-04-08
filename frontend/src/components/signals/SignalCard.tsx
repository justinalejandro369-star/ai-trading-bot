import { Card, CardContent } from '@/components/ui/card'
import type { Signal } from '@/types'

function directionClass(direction: string) {
  if (direction === 'BUY') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
  if (direction === 'SELL') return 'bg-red-500/20 text-red-400 border-red-500/40'
  return 'bg-slate-500/20 text-slate-400 border-slate-500/40'
}

function multiframeBadgeClass(direction: string) {
  if (direction === 'BUY') return 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/50'
  if (direction === 'SELL') return 'bg-red-900/60 text-red-300 border border-red-700/50'
  return 'bg-slate-700/60 text-slate-300 border border-slate-600/50'
}

function fmt(val: number | null, prefix = '$') {
  if (val === null) return '—'
  return `${prefix}${val.toFixed(2)}`
}

interface MultiframeAgreement {
  '1H'?: string
  '4H'?: string
  '1D'?: string
  agreement: boolean
}

export default function SignalCard({ signal }: { signal: Signal }) {
  const multiframe = (signal.multiframe_agreement ?? { agreement: false }) as MultiframeAgreement
  const intervals = ['1H', '4H', '1D'] as const
  const hasMultiframe = intervals.some((i) => multiframe[i] !== undefined)

  return (
    <Card
      data-testid={`signal-${signal.symbol.toLowerCase()}`}
      className="bg-slate-800 border-slate-700"
    >
      <CardContent className="p-4 space-y-2">
        {/* Header row: direction badge, symbol, regime */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${directionClass(signal.direction)}`}
          >
            {signal.direction}
          </span>
          <span className="font-bold text-slate-100">{signal.symbol}</span>
          <span className="text-xs text-slate-500 italic ml-auto">{signal.regime}</span>
        </div>

        {/* Confidence bar */}
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

        {/* Price levels */}
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

        {/* Multi-timeframe agreement badges */}
        {hasMultiframe && (
          <div className="flex items-center gap-1.5 pt-1">
            <span className="text-xs text-slate-500 mr-0.5">Timeframes:</span>
            {intervals.map((tf) => {
              const dir = multiframe[tf]
              if (!dir) return null
              return (
                <span
                  key={tf}
                  data-testid={`multiframe-${signal.symbol.toLowerCase()}-${tf.toLowerCase()}`}
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-mono ${multiframeBadgeClass(dir)}`}
                >
                  {tf} <span className="font-semibold">{dir}</span>
                </span>
              )
            })}
            {multiframe.agreement && (
              <span className="ml-auto text-xs text-emerald-400 font-medium">Aligned</span>
            )}
          </div>
        )}

        {/* LLM explanation */}
        {signal.explanation && signal.explanation.trim().length > 0 && (
          <div
            data-testid={`explanation-${signal.symbol.toLowerCase()}`}
            className="mt-2 text-xs text-slate-400 bg-slate-900/50 rounded p-2 leading-relaxed border border-slate-700/50"
          >
            {signal.explanation}
          </div>
        )}

        {/* Top signal reasons (shown when no explanation) */}
        {(!signal.explanation || signal.explanation.trim().length === 0) &&
          signal.reasons.slice(0, 2).length > 0 && (
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
