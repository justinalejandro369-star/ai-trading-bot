import { test, expect } from '@playwright/test'
import { loginViaCookie } from './helpers'

const SIGNALS_WITH_LLM = [
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
    reasons: ['RSI bullish', 'MACD above signal line'],
    interval: '1D',
    scanned_at: '2026-04-08T12:00:00',
    explanation: 'Strong bullish momentum with RSI and MACD aligned.',
    multiframe_agreement: { '1D': 'BUY', agreement: false },
    llm_adjustment: 5,
    llm_reasoning: 'Bullish divergence pattern detected with rising volume confirms momentum.',
    llm_patterns: ['bullish divergence', 'volume confirmation'],
  },
]

test.describe('Signal Cards with LLM Insights', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaCookie(page)

    // Mock endpoints
    await page.route('**/api/signals/top**', (route) =>
      route.fulfill({ status: 200, json: SIGNALS_WITH_LLM }),
    )
    await page.route('**/api/market-data/**', (route) =>
      route.fulfill({ status: 200, json: [] }),
    )
    await page.route('**/api/indicators/**', (route) =>
      route.fulfill({ status: 200, json: {} }),
    )

    await page.goto('/dashboard')
  })

  test('displays LLM patterns as badges', async ({ page }) => {
    // Navigate to Market Scanner via sidebar
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()

    // Verify LLM pattern badges are rendered
    const patternBadges = page.getByTestId('llm-pattern-aapl')
    await expect(patternBadges.first()).toBeVisible()
    await expect(patternBadges.first()).toContainText('bullish divergence')
  })

  test('displays LLM reasoning text', async ({ page }) => {
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()

    const reasoning = page.getByTestId('llm-reasoning-aapl')
    await expect(reasoning).toBeVisible()
    await expect(reasoning).toContainText('Bullish divergence pattern detected')
  })

  test('displays LLM adjustment indicator', async ({ page }) => {
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()

    // The +5 adjustment should appear
    await expect(page.getByText('AI: +5')).toBeVisible()
  })
})
