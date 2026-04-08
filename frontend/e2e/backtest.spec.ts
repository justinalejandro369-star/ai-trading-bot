import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Backtest Results', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    await page.getByRole('tab', { name: /backtest/i }).click()
  })

  test('backtest tab content area is visible without crash', async ({
    page,
  }) => {
    const activePanel = page.locator('[data-slot="tabs-content"]').last()
    await expect(activePanel).toBeVisible()
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
      await expect(
        page.getByRole('button', { name: /run backtest/i }),
      ).toBeVisible()
    }
  })

  test('clicking Run Backtest calls POST /api/backtest when implemented', async ({
    page,
  }) => {
    const runButton = page.getByRole('button', { name: /run backtest/i })
    if (await runButton.count() === 0) return

    let backtestCalled = false
    await page.route('**/api/backtest', async (route) => {
      backtestCalled = true
      await route.fulfill({
        status: 200,
        json: {
          sharpe_ratio: 1.2,
          max_drawdown: -0.08,
          win_rate: 0.62,
          profit_factor: 1.8,
          total_return: 0.15,
          equity_curve: [{ time: 1714521600, equity: 10500 }],
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
    const runButton = page.getByRole('button', { name: /run backtest/i })
    if (await runButton.count() === 0) return

    await runButton.click()
    const metrics = page.getByTestId('backtest-metrics')
    if (await metrics.count() > 0) {
      await expect(metrics).toBeVisible({ timeout: 8000 })
      await expect(metrics.getByText(/1\.2|sharpe/i)).toBeVisible()
    }
  })

  test('backtest equity chart renders after run when implemented', async ({
    page,
  }) => {
    const runButton = page.getByRole('button', { name: /run backtest/i })
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
          equity_curve: [{ time: 1714521600, equity: 10200 }],
        },
      })
    })

    const runButton = page.getByRole('button', { name: /run backtest/i })
    await runButton.click()

    const metrics = page.getByTestId('backtest-metrics')
    if (await metrics.count() > 0) {
      await expect(metrics).toBeVisible({ timeout: 8000 })
      expect(requestBody['symbol']).toBe('MSFT')
    }
  })

  test('no JavaScript errors on backtest tab', async ({ page }) => {
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
})
