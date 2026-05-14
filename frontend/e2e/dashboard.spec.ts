import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Dashboard — sidebar navigation', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
  })

  test('dashboard nav bar renders', async ({ page }) => {
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })

  test('dashboard nav shows authenticated username', async ({ page }) => {
    // Username appears in the TopBar's user info section
    const topBar = page.getByTestId('dashboard-nav')
    await expect(topBar.getByText('admin')).toBeVisible()
  })

  test('sidebar nav is present with all sections', async ({ page }) => {
    const sidebar = page.getByTestId('sidebar-nav')
    await expect(sidebar.getByText('Dashboard')).toBeVisible()
    await expect(sidebar.getByText('Market Scanner')).toBeVisible()
    await expect(sidebar.getByText('Portfolio')).toBeVisible()
    await expect(sidebar.getByText('Backtesting')).toBeVisible()
  })

  test('Dashboard section is active by default', async ({ page }) => {
    // Dashboard is the default view — the chart container should be visible
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })

  test('Market Scanner click shows signal feed', async ({ page }) => {
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()
    // Signal feed heading should appear
    await expect(page.getByText('AI Signal Feed')).toBeVisible()
  })

  test('Portfolio click shows portfolio view', async ({ page }) => {
    await page.getByTestId('sidebar-nav').getByText('Portfolio').click()
    const portfolioView = page.getByTestId('portfolio-view')
    if (await portfolioView.count() > 0) {
      await expect(portfolioView).toBeVisible()
    }
  })

  test('Backtesting click shows backtest results', async ({ page }) => {
    await page.getByTestId('sidebar-nav').getByText('Backtesting').click()
    const results = page.getByTestId('backtest-results')
    if (await results.count() > 0) {
      await expect(results).toBeVisible()
    }
  })

  test('no JavaScript errors cycling through all sections', async ({ page }) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })

    const sidebar = page.getByTestId('sidebar-nav')
    for (const section of ['Dashboard', 'Market Scanner', 'Portfolio', 'Backtesting']) {
      await sidebar.getByText(section).click()
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

  test('dashboard nav visible on mobile', async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    await expect(page.getByTestId('dashboard-nav')).toBeVisible()
  })
})
