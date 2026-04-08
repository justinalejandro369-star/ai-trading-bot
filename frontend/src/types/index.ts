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
