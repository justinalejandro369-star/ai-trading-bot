import type { Page } from '@playwright/test'

const SIGNALS_MOCK = [
  {
    symbol: 'AAPL',
    direction: 'BUY',
    confidence: 85,
    regime: 'trending',
    close: 171.8,
    entry_price: 172.0,
    stop_loss: 168.0,
    target_price: 180.0,
    rsi_14: 55.2,
    macd_val: 1.34,
    adx_14: 28.5,
    atr_14: 2.1,
    reasons: ['RSI bullish'],
    interval: '1D',
    scanned_at: '2026-04-08T12:00:00',
    explanation: '',
    multiframe_agreement: { agreement: false },
    llm_adjustment: 0,
    llm_reasoning: '',
    llm_patterns: [],
  },
]

// Backend returns ISO timestamp strings; api/market.ts converts to Unix seconds for the chart
const CANDLES_MOCK = [
  { timestamp: '2026-04-08T00:00:00', open: 172, high: 173, low: 171, close: 172.5, volume: 1000000 },
  { timestamp: '2026-04-07T00:00:00', open: 170, high: 172, low: 169, close: 171.8, volume: 950000 },
]

// Field names match the backend's GET /api/paper/accounts/{id} response
const ACCOUNT_MOCK = {
  id: 1,
  name: 'Paper Account',
  cash_balance: 95000,
  starting_balance: 100000,
  total_equity: 95000,
  slippage_std: 0.001,
  commission: 0.001,
  backtest_run_id: null,
  open_positions: [
    {
      symbol: 'AAPL',
      interval: '1d',
      quantity: 10,
      avg_entry_price: 170,
    },
  ],
}

// Backend returns { account_id, equity_curve: [[iso_string, value], ...] }
const EQUITY_MOCK = {
  account_id: 1,
  equity_curve: [['2026-04-08T12:00:00', 95200]],
}

// equity_curve is [[iso_string, value], ...] tuples (matches _serialize_equity in engine.py)
const BACKTEST_MOCK = {
  sharpe_ratio: 1.2,
  max_drawdown: -0.08,
  win_rate: 0.62,
  profit_factor: 1.8,
  total_return: 0.15,
  total_trades: 5,
  equity_curve: [['2026-04-08T00:00:00', 10500]],
}

export async function mockBackend(page: Page): Promise<void> {
  // Auth
  await page.route('**/auth/me', (route) =>
    route.fulfill({ status: 200, json: { username: 'admin' } }),
  )

  // Signals
  await page.route('**/api/signals/top**', (route) =>
    route.fulfill({ status: 200, json: SIGNALS_MOCK }),
  )

  // Market data (candles)
  await page.route('**/api/market-data/**', (route) =>
    route.fulfill({ status: 200, json: CANDLES_MOCK }),
  )

  // Indicators
  await page.route('**/api/indicators/**', (route) =>
    route.fulfill({ status: 200, json: { rsi_14: 55.2, macd: 1.34 } }),
  )

  // Paper trading account
  await page.route('**/api/paper/accounts/1', (route) =>
    route.fulfill({ status: 200, json: ACCOUNT_MOCK }),
  )

  // Equity history
  await page.route('**/api/paper/accounts/1/equity', (route) =>
    route.fulfill({ status: 200, json: EQUITY_MOCK }),
  )

  // Compare paper vs backtest
  await page.route('**/api/paper/accounts/1/compare', (route) =>
    route.fulfill({
      status: 200,
      json: { paper_return: 5.2, backtest_return: 7.1 },
    }),
  )

  // Backtest — run
  await page.route('**/api/backtest', (route) => {
    // Only match exact POST /api/backtest, not /api/backtest/runs*
    if (route.request().url().includes('/api/backtest/runs')) return route.fallback()
    return route.fulfill({ status: 200, json: BACKTEST_MOCK })
  })

  // Backtest — list runs (Performance Audit)
  await page.route('**/api/backtest/runs', (route) =>
    route.fulfill({
      status: 200,
      json: [
        {
          id: 1,
          symbol: 'AAPL',
          interval: '1D',
          run_at: '2026-04-08T12:00:00',
          sharpe_ratio: 1.2,
          max_drawdown: 0.08,
          win_rate: 0.62,
          profit_factor: 1.8,
          total_return: 0.15,
          total_trades: 5,
          commission: 0.001,
          slippage: 0.001,
          init_cash: 10000,
        },
      ],
    }),
  )

  // Backtest — single run detail (Performance Audit)
  await page.route('**/api/backtest/runs/*', (route) =>
    route.fulfill({
      status: 200,
      json: {
        id: 1,
        symbol: 'AAPL',
        interval: '1D',
        run_at: '2026-04-08T12:00:00',
        sharpe_ratio: 1.2,
        max_drawdown: 0.08,
        win_rate: 0.62,
        profit_factor: 1.8,
        total_return: 0.15,
        total_trades: 5,
        commission: 0.001,
        slippage: 0.001,
        init_cash: 10000,
        equity_curve: [['2026-04-08T00:00:00', 10500]],
      },
    }),
  )

  // Chat
  await page.route('**/api/chat/message', (route) =>
    route.fulfill({ status: 200, json: { reply: 'Mock chat response.' } }),
  )

  // Logout
  await page.route('**/auth/logout', (route) =>
    route.fulfill({ status: 200, json: { status: 'ok' } }),
  )
}

export async function loginViaUI(page: Page): Promise<void> {
  await page.route('**/auth/login', (route) =>
    route.fulfill({ status: 200, json: { status: 'ok' } }),
  )
  await page.route('**/auth/me', (route) =>
    route.fulfill({ status: 200, json: { username: 'admin' } }),
  )
  await page.route('**/api/**', (route) =>
    route.fulfill({ status: 200, json: [] }),
  )

  await page.goto('/login')
  await page.getByLabel(/username/i).fill('admin')
  await page.getByLabel(/password/i).fill('testpassword')
  await page.getByRole('button', { name: /sign in/i }).click()
}

export async function loginViaCookie(page: Page): Promise<void> {
  await page.route('**/auth/me', (route) =>
    route.fulfill({ status: 200, json: { username: 'admin' } }),
  )
}
