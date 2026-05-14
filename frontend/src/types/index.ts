export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface MultiframeAgreement {
  '1H'?: string
  '4H'?: string
  '1D'?: string
  agreement: boolean
}

export interface Signal {
  symbol: string
  interval: string
  scanned_at: string
  direction: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  regime: string
  close: number
  entry_price: number | null
  stop_loss: number | null
  target_price: number | null
  rsi_14: number | null
  macd_val: number | null
  adx_14: number | null
  atr_14: number | null
  reasons: string[]
  explanation: string
  multiframe_agreement: MultiframeAgreement
  llm_adjustment: number
  llm_reasoning: string
  llm_patterns: string[]
}

export interface PaperPosition {
  symbol: string
  interval: string
  quantity: number
  avg_entry_price: number
}

export interface PaperAccount {
  id: number
  name: string
  cash_balance: number
  starting_balance: number
  total_equity: number
  open_positions: PaperPosition[]
}

export interface EquityPoint {
  recorded_at: string
  equity: number
}

export interface BacktestResult {
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  profit_factor: number
  total_return: number
  total_trades: number
  equity_curve: [string, number][]
}

// Summary returned by GET /api/backtest/runs (no equity_curve — too large for list)
export interface BacktestRunSummary {
  id: number
  symbol: string
  interval: string
  run_at: string
  sharpe_ratio: number | null
  max_drawdown: number | null
  win_rate: number | null
  profit_factor: number | null
  total_return: number | null
  total_trades: number | null
  commission: number
  slippage: number
  init_cash: number
}

// Full detail returned by GET /api/backtest/runs/{id} (includes equity_curve)
export interface BacktestRunDetail extends BacktestRunSummary {
  equity_curve: [string, number][]
}

// ---------- Chart Overlay Types ----------

export interface IndicatorSeries {
  symbol: string
  interval: string
  timestamps: string[]
  ema_50: (number | null)[]
  ema_200: (number | null)[]
  bb_upper: (number | null)[]
  bb_lower: (number | null)[]
  bb_mid: (number | null)[]
  rsi_14: (number | null)[]
  macd_val: (number | null)[]
  macd_signal: (number | null)[]
  macd_hist: (number | null)[]
  volume: number[]
  vol_sma_20: (number | null)[]
}

export interface FibonacciLevels {
  swing_high: number
  swing_low: number
  swing_high_time: string
  swing_low_time: string
  trend_direction: 'up' | 'down'
  retracement: Record<string, number>
  extension: Record<string, number>
}

export interface TrendLine {
  start_time: string
  start_price: number
  end_time: string
  end_price: number
  slope: number
  direction: 'ascending' | 'descending'
  touches: number
  strength: number
}

export interface SRLevel {
  price: number
  level_type: 'support' | 'resistance' | 'both'
  touches: number
  first_touch_time: string
  last_touch_time: string
  strength: number
}

export interface PivotPointSet {
  method: string
  pivot: number
  r1: number
  r2: number
  r3: number
  s1: number
  s2: number
  s3: number
}

export interface ChartAnalysis {
  symbol: string
  interval: string
  fibonacci: FibonacciLevels | null
  trendlines: { lines: TrendLine[] }
  support_resistance: { levels: SRLevel[] }
  pivots: PivotPointSet | null
}
