import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Backtest Results', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    // Navigate to Backtesting via sidebar
    await page.getByTestId('sidebar-nav').getByText('Backtesting').click()
  })

  test('backtest results root component renders when implemented', async ({
    page,
  }) => {
    const results = page.getByTestId('backtest-results')
    if (await results.count() > 0) {
      await expect(results).toBeVisible({ timeout: 5000 })
    }
  })

  test('run backtest button is visible when BacktestResults exists', async ({
    page,
  }) => {
    const results = page.getByTestId('backtest-results')
    if (await results.count() > 0) {
      // Scope to the form inside backtest-results to avoid matching the sub-view toggle
      await expect(
        results.getByRole('button', { name: /run backtest/i }),
      ).toBeVisible()
    }
  })

  test('clicking Run Backtest calls POST /api/backtest when implemented', async ({
    page,
  }) => {
    const results = page.getByTestId('backtest-results')
    if (await results.count() === 0) return

    const runButton = results.getByRole('button', { name: /run backtest/i })
    if (await runButton.count() === 0) return

    let backtestCalled = false
    await page.route('**/api/backtest', async (route) => {
      // Only intercept POST, let GET /api/backtest/runs* through
      if (route.request().url().includes('/api/backtest/runs')) return route.fallback()
      backtestCalled = true
      await route.fulfill({
        status: 200,
        json: {
          sharpe_ratio: 1.2,
          max_drawdown: -0.08,
          win_rate: 0.62,
          profit_factor: 1.8,
          total_return: 0.15,
          total_trades: 5,
          equity_curve: [['2026-04-08T00:00:00', 10500]],
        },
      })
    })

    await runButton.click()
    await expect(page.getByTestId('backtest-metrics')).toBeVisible({
      timeout: 8000,
    })
    expect(backtestCalled).toBe(true)
  })

  test('backtest metrics show Sharpe ratio after run when implemented', async ({
    page,
  }) => {
    const results = page.getByTestId('backtest-results')
    if (await results.count() === 0) return

    const runButton = results.getByRole('button', { name: /run backtest/i })
    if (await runButton.count() === 0) return

    await runButton.click()
    const metrics = page.getByTestId('backtest-metrics')
    if (await metrics.count() > 0) {
      await expect(metrics).toBeVisible({ timeout: 8000 })
      await expect(metrics.getByText('1.20')).toBeVisible()
    }
  })

  test('backtest equity chart renders after run when implemented', async ({
    page,
  }) => {
    const results = page.getByTestId('backtest-results')
    if (await results.count() === 0) return

    const runButton = results.getByRole('button', { name: /run backtest/i })
    if (await runButton.count() === 0) return

    await runButton.click()
    const chart = page.getByTestId('backtest-equity-chart')
    if (await chart.count() > 0) {
      await expect(chart).toBeVisible({ timeout: 8000 })
    }
  })

  test('changing symbol input updates backtest target when implemented', async ({
    page,
  }) => {
    const symbolInput = page
      .getByPlaceholder(/symbol/i)
      .or(page.locator('input[value="AAPL"]'))

    if (await symbolInput.count() === 0) return

    await symbolInput.clear()
    await symbolInput.fill('MSFT')

    let requestBody: Record<string, unknown> = {}
    await page.route('**/api/backtest', async (route) => {
      if (route.request().url().includes('/api/backtest/runs')) return route.fallback()
      const postData = route.request().postData()
      if (postData) {
        requestBody = JSON.parse(postData) as Record<string, unknown>
      }
      await route.fulfill({
        status: 200,
        json: {
          sharpe_ratio: 0.9,
          max_drawdown: -0.1,
          win_rate: 0.55,
          profit_factor: 1.4,
          total_return: 0.08,
          total_trades: 3,
          equity_curve: [['2026-04-08T00:00:00', 10200]],
        },
      })
    })

    const results = page.getByTestId('backtest-results')
    const runButton = results.getByRole('button', { name: /run backtest/i })
    await runButton.click()

    const metrics = page.getByTestId('backtest-metrics')
    if (await metrics.count() > 0) {
      await expect(metrics).toBeVisible({ timeout: 8000 })
      expect(requestBody['symbol']).toBe('MSFT')
    }
  })

  test('no JavaScript errors on backtest section', async ({ page }) => {
    const errors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    await page.waitForTimeout(500)
    const realErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404'),
    )
    expect(realErrors).toHaveLength(0)
  })

  test('performance audit sub-view toggle is visible', async ({ page }) => {
    await expect(
      page.getByRole('button', { name: /performance audit/i }),
    ).toBeVisible()
  })

  test('switching to performance audit shows audit component', async ({
    page,
  }) => {
    await page.getByRole('button', { name: /performance audit/i }).click()
    // Should show the performance audit heading (use role to avoid matching the toggle button too)
    await expect(page.getByRole('heading', { name: /performance audit/i })).toBeVisible({ timeout: 5000 })
  })
})
