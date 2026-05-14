import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const features = [
  {
    title: 'Real-Time Signal Feed',
    description:
      'AI scans 50+ stocks and crypto assets every 5 minutes and surfaces the highest-confidence opportunities.',
  },
  {
    title: 'Candlestick Charts',
    description:
      'TradingView-quality charts with RSI, MACD, and Bollinger Band overlays rendered at 100k+ bars.',
  },
  {
    title: 'Paper Trading',
    description:
      'Practice with a $100,000 simulated portfolio. Track every position, fill, and P&L without risking real money.',
  },
  {
    title: 'Backtest Strategies',
    description:
      'Validate signals against years of historical data. See Sharpe ratio, max drawdown, and win rate instantly.',
  },
  {
    title: 'Market Regime Detection',
    description:
      'Know whether the market is trending, ranging, or volatile before placing any trade.',
  },
  {
    title: 'Risk Management',
    description:
      'Every signal includes a stop-loss level and confidence score so you always know your downside.',
  },
]

export default function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#111417] text-[var(--kt-on-surface)]">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center px-4 pt-24 pb-20 text-center">
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage:
              'linear-gradient(#424654 1px, transparent 1px), linear-gradient(90deg, #424654 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />
        <div className="relative z-10 max-w-3xl">
          <h1 className="text-5xl font-bold tracking-tight mb-6 bg-gradient-to-r from-[#B2C5FF] to-[#44E092] bg-clip-text text-transparent">
            AI-Powered Trading Intelligence
          </h1>
          <p className="text-xl text-[var(--kt-on-surface-variant)] mb-10 leading-relaxed">
            Scan stocks and crypto in real-time. Surface high-confidence
            opportunities. Make faster, smarter decisions.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Button
              size="lg"
              className="bg-gradient-to-r from-[var(--kt-primary-container)] to-[var(--kt-secondary-container)] text-white hover:opacity-90"
              onClick={() => navigate('/login')}
            >
              Start Trading
            </Button>
            <Button
              size="lg"
              variant="ghost"
              className="text-[var(--kt-on-surface-variant)] hover:bg-[var(--kt-surface-container-high)] hover:text-[var(--kt-on-surface)]"
              onClick={() => navigate('/dashboard')}
            >
              View Demo
            </Button>
          </div>
        </div>
      </section>

      {/* Feature grid — No-Line Rule: tonal background shift */}
      <section className="max-w-6xl mx-auto px-4 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <Card key={feature.title} className="bg-[var(--kt-surface-container-low)] border-none">
              <CardHeader>
                <CardTitle className="text-[var(--kt-on-surface)] text-lg">
                  {feature.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-[var(--kt-on-surface-variant)] text-sm leading-relaxed">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[rgba(66,70,84,0.15)] py-8 text-center text-[var(--kt-on-surface-variant)] text-sm">
        Built with Python + FastAPI + React. Zero data costs.
      </footer>
    </div>
  )
}
