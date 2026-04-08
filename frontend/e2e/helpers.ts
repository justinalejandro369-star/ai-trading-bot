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
  },
]

const CANDLES_MOCK = [
  { time: 1714608000, open: 172, high: 173, low: 171, close: 172.5 },
  { time: 1714521600, open: 170, high: 172, low: 169, close: 171.8 },
]

const ACCOUNT_MOCK = {
  id: 1,
  name: 'Paper Account',
  balance: 95000,
  initial_balance: 100000,
  positions: [
    {
      symbol: 'AAPL',
      quantity: 10,
      avg_price: 170,
      current_price: 172,
      pnl: 20,
    },
  ],
}

const EQUITY_MOCK = [{ recorded_at: '2026-04-08T12:00:00', equity: 95200 }]

const BACKTEST_MOCK = {
  sharpe_ratio: 1.2,
  max_drawdown: -0.08,
  win_rate: 0.62,
  profit_factor: 1.8,
  total_return: 0.15,
  equity_curve: [{ time: 1714521600, equity: 10500 }],
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

  // Backtest
  await page.route('**/api/backtest', (route) =>
    route.fulfill({ status: 200, json: BACKTEST_MOCK }),
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
