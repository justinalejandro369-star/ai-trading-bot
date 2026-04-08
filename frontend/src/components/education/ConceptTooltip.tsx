import { useState } from 'react'

interface ConceptTooltipProps {
  slug: string
  children: React.ReactNode
}

interface Concept {
  name: string
  short: string
  explanation: string
}

const INLINE_CONCEPTS: Record<string, Concept> = {
  rsi: {
    name: 'RSI (Relative Strength Index)',
    short: 'Momentum oscillator: 0-100 scale.',
    explanation:
      'Below 30 = oversold (potential bounce). Above 70 = overbought (potential pullback). ' +
      'Between 30-70 = neutral.',
  },
  macd: {
    name: 'MACD',
    short: 'Trend momentum indicator.',
    explanation:
      'MACD line crossing above signal line = bullish momentum. ' +
      'Crossing below = bearish momentum.',
  },
  'bollinger-bands': {
    name: 'Bollinger Bands',
    short: 'Volatility bands around a moving average.',
    explanation:
      'Price touching the upper band may signal overbought. Lower band may signal oversold. ' +
      'Narrow bands (squeeze) often precede a big move.',
  },
  adx: {
    name: 'ADX',
    short: 'Measures trend strength (not direction).',
    explanation:
      'Below 20 = weak/no trend (ranging). Above 25 = strong trend. ' +
      'Combine with MACD or RSI to determine direction.',
  },
  atr: {
    name: 'ATR (Average True Range)',
    short: 'Measures daily price volatility.',
    explanation:
      'Higher ATR = more volatile market. Stop-losses are typically set at 1.5x ATR ' +
      'from entry to avoid normal noise.',
  },
}

export default function ConceptTooltip({ slug, children }: ConceptTooltipProps) {
  const [visible, setVisible] = useState(false)
  const concept = INLINE_CONCEPTS[slug]

  if (!concept) return <>{children}</>

  return (
    <span className="relative inline-block">
      <span
        data-testid={`tooltip-trigger-${slug}`}
        className="cursor-help underline decoration-dotted decoration-blue-400 text-blue-300"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        tabIndex={0}
      >
        {children}
      </span>
      {visible && (
        <div
          data-testid={`tooltip-content-${slug}`}
          className="absolute z-50 bottom-full left-0 mb-2 w-72 rounded-lg border border-slate-600 bg-slate-800 p-3 shadow-xl text-sm"
          role="tooltip"
        >
          <p className="font-semibold text-blue-300 mb-1">{concept.name}</p>
          <p className="text-slate-300 text-xs mb-2">{concept.short}</p>
          <p className="text-slate-400 text-xs leading-relaxed">{concept.explanation}</p>
        </div>
      )}
    </span>
  )
}
