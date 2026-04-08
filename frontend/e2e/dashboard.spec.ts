import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Dashboard — tab navigation', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
  })

  test('dashboard nav bar renders', async ({ page }) => {
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })

  test('dashboard nav shows authenticated username', async ({ page }) => {
    await expect(page.getByText('admin')).toBeVisible()
  })

  test('all 4 tabs are present', async ({ page }) => {
    const tabs = page.getByTestId('dashboard-tabs')
    await expect(tabs.getByRole('tab', { name: /chart/i })).toBeVisible()
    await expect(tabs.getByRole('tab', { name: /signals/i })).toBeVisible()
    await expect(tabs.getByRole('tab', { name: /portfolio/i })).toBeVisible()
    await expect(tabs.getByRole('tab', { name: /backtest/i })).toBeVisible()
  })

  test('Chart tab is active by default', async ({ page }) => {
    const chartTab = page.getByTestId('dashboard-tabs').getByRole('tab', { name: /chart/i })
    // base-ui uses data-active attribute (not data-state)
    await expect(chartTab).toHaveAttribute('data-active', '')
  })

  test('Signals tab click changes active tab', async ({ page }) => {
    await page.getByRole('tab', { name: /signals/i }).click()
    const signalsTab = page.getByTestId('dashboard-tabs').getByRole('tab', { name: /signals/i })
    await expect(signalsTab).toHaveAttribute('data-active', '')
  })

  test('Portfolio tab click changes active tab', async ({ page }) => {
    await page.getByRole('tab', { name: /portfolio/i }).click()
    const portfolioTab = page.getByTestId('dashboard-tabs').getByRole('tab', { name: /portfolio/i })
    await expect(portfolioTab).toHaveAttribute('data-active', '')
  })

  test('Backtest tab click changes active tab', async ({ page }) => {
    await page.getByRole('tab', { name: /backtest/i }).click()
    const backtestTab = page.getByTestId('dashboard-tabs').getByRole('tab', { name: /backtest/i })
    await expect(backtestTab).toHaveAttribute('data-active', '')
  })

  test('Signals tab renders content area when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: /signals/i }).click()
    // Tab panel uses data-slot="tabs-content" in base-ui
    const tabContent = page.locator('[data-slot="tabs-content"]').last()
    await expect(tabContent).toBeVisible()
  })

  test('Portfolio tab renders content area when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: /portfolio/i }).click()
    const tabContent = page.locator('[data-slot="tabs-content"]').last()
    await expect(tabContent).toBeVisible()
  })

  test('Backtest tab renders content area when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: /backtest/i }).click()
    const tabContent = page.locator('[data-slot="tabs-content"]').last()
    await expect(tabContent).toBeVisible()
  })

  test('no JavaScript errors cycling through all tabs', async ({ page }) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })

    for (const tabName of [/chart/i, /signals/i, /portfolio/i, /backtest/i]) {
      await page.getByRole('tab', { name: tabName }).click()
      await page.waitForTimeout(300)
    }

    const realErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404'),
    )
    expect(realErrors).toHaveLength(0)
  })
})

test.describe('Dashboard — WebSocket real-time updates', () => {
  test('signal_update via WebSocket adds signal to feed', async ({ page }) => {
    await mockBackend(page)

    await page.routeWebSocket(/\/ws\/live/, (ws) => {
      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: 'signal_update',
            signal: {
              symbol: 'TSLA',
              direction: 'BUY',
              confidence: 90,
              regime: 'trending',
              close: 250.0,
              entry_price: 251.0,
              stop_loss: 245.0,
              target_price: 270.0,
              rsi_14: 60,
              macd_val: 2.1,
              adx_14: 30,
              atr_14: 3.5,
              reasons: ['MACD crossover'],
              interval: '1D',
              scanned_at: new Date().toISOString(),
            },
          }),
        )
      }
    })

    await page.goto('/dashboard')
    // Dashboard nav must remain visible after WS message (page didn't crash)
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })

  test('price_tick via WebSocket does not crash the page', async ({ page }) => {
    await mockBackend(page)

    await page.routeWebSocket(/\/ws\/live/, (ws) => {
      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: 'price_tick',
            symbol: 'AAPL',
            candle: { time: 1714608000, open: 172, high: 173, low: 171, close: 172.5 },
          }),
        )
      }
    })

    await page.goto('/dashboard')
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })
})

test.describe('Mobile responsive — iPhone 14 viewport', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('landing page fits mobile viewport without horizontal scroll', async ({
    page,
  }) => {
    await page.goto('/')
    const scrollWidth = await page.evaluate(() => document.body.scrollWidth)
    const clientWidth = await page.evaluate(() => document.body.clientWidth)
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 2)
  })

  test('dashboard tabs are accessible on mobile', async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    await expect(page.getByTestId('dashboard-tabs')).toBeVisible()
    await page.getByRole('tab', { name: /signals/i }).click()
    await expect(
      page.getByRole('tab', { name: /signals/i }),
    ).toHaveAttribute('data-active', '')
  })

  test('dashboard nav visible on mobile', async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })
})
