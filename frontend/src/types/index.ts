export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
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
}

export interface PaperPosition {
  symbol: string
  quantity: number
  avg_price: number
  current_price: number
  pnl: number
}

export interface PaperAccount {
  id: number
  name: string
  balance: number
  initial_balance: number
  positions: PaperPosition[]
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
  equity_curve: { time: number; equity: number }[]
}
