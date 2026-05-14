import { Card, CardContent } from '@/components/ui/card'
import type { Signal } from '@/types'

function directionClass(direction: string) {
  if (direction === 'BUY') return 'bg-[#03C177]/20 text-[#44E092]'
  if (direction === 'SELL') return 'bg-[#FF5451]/20 text-[#FFB3AD]'
  return 'bg-[var(--kt-surface-container-high)] text-[var(--kt-on-surface-variant)]'
}

function multiframeBadgeClass(direction: string) {
  if (direction === 'BUY') return 'bg-[#03C177]/15 text-[#44E092] border border-[#03C177]/30'
  if (direction === 'SELL') return 'bg-[#FF5451]/15 text-[#FFB3AD] border border-[#FF5451]/30'
  return 'bg-[var(--kt-surface-container-high)] text-[var(--kt-on-surface-variant)] border border-[rgba(66,70,84,0.15)]'
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
      className="bg-[var(--kt-surface-container-low)] border-none"
    >
      <CardContent className="p-4 space-y-2">
        {/* Header row: direction badge, symbol, regime */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${directionClass(signal.direction)}`}
          >
            {signal.direction}
          </span>
          <span className="font-bold text-[var(--kt-on-surface)]">{signal.symbol}</span>
          <span className="text-xs text-[var(--kt-on-surface-variant)] italic ml-auto">{signal.regime}</span>
        </div>

        {/* Confidence bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-[var(--kt-on-surface-variant)]">
            <span>Confidence</span>
            <span>{signal.confidence}%</span>
          </div>
          <div className="h-1.5 w-full rounded bg-[var(--kt-surface-container-highest)]">
            <div
              className="h-1.5 rounded bg-[var(--kt-secondary)]"
              style={{ width: `${signal.confidence}%` }}
            />
          </div>
        </div>

        {/* Price levels */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <div className="label-terminal text-[var(--kt-on-surface-variant)]">Entry</div>
            <div className="font-mono text-[var(--kt-on-surface)]">{fmt(signal.entry_price)}</div>
          </div>
          <div>
            <div className="label-terminal text-[var(--kt-on-surface-variant)]">Stop-Loss</div>
            <div className="font-mono text-[var(--kt-tertiary-container)]">{fmt(signal.stop_loss)}</div>
          </div>
          <div>
            <div className="label-terminal text-[var(--kt-on-surface-variant)]">Target</div>
            <div className="font-mono text-[var(--kt-secondary)]">{fmt(signal.target_price)}</div>
          </div>
        </div>

        {/* Multi-timeframe agreement badges */}
        {hasMultiframe && (
          <div className="flex items-center gap-1.5 pt-1">
            <span className="text-xs text-[var(--kt-on-surface-variant)] mr-0.5">Timeframes:</span>
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
              <span className="ml-auto text-xs text-[var(--kt-secondary)] font-medium">Aligned</span>
            )}
          </div>
        )}

        {/* LLM advisory patterns — shown as badges when LLM scoring is active */}
        {signal.llm_patterns && signal.llm_patterns.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {signal.llm_patterns.map((pattern, i) => (
              <span
                key={i}
                data-testid={`llm-pattern-${signal.symbol.toLowerCase()}`}
                className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-[var(--kt-primary-container)]/15 text-[var(--primary)] border border-[var(--kt-primary-container)]/30"
              >
                {pattern}
              </span>
            ))}
            {signal.llm_adjustment !== 0 && (
              <span className={`ml-auto text-xs font-medium ${signal.llm_adjustment > 0 ? 'text-[var(--kt-secondary)]' : 'text-[var(--kt-tertiary-container)]'}`}>
                AI: {signal.llm_adjustment > 0 ? '+' : ''}{signal.llm_adjustment}
              </span>
            )}
          </div>
        )}

        {/* LLM reasoning — shows the AI's analysis when available */}
        {signal.llm_reasoning && signal.llm_reasoning.trim().length > 0 && (
          <div
            data-testid={`llm-reasoning-${signal.symbol.toLowerCase()}`}
            className="text-xs text-[var(--primary)]/80 bg-[var(--kt-primary-container)]/10 rounded p-2 leading-relaxed"
          >
            {signal.llm_reasoning}
          </div>
        )}

        {/* LLM explanation */}
        {signal.explanation && signal.explanation.trim().length > 0 && (
          <div
            data-testid={`explanation-${signal.symbol.toLowerCase()}`}
            className="mt-2 text-xs text-[var(--kt-on-surface-variant)] bg-[var(--kt-surface-container-lowest)] rounded p-2 leading-relaxed"
          >
            {signal.explanation}
          </div>
        )}

        {/* Top signal reasons (shown when no explanation) */}
        {(!signal.explanation || signal.explanation.trim().length === 0) &&
          signal.reasons.slice(0, 2).length > 0 && (
            <ul className="text-xs text-[var(--kt-on-surface-variant)] space-y-0.5">
              {signal.reasons.slice(0, 2).map((r, i) => (
                <li key={i}>• {r}</li>
              ))}
            </ul>
          )}
      </CardContent>
    </Card>
  )
}
