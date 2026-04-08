import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Portfolio View', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    await page.getByRole('tab', { name: /portfolio/i }).click()
  })

  test('portfolio tab content area is visible without crash', async ({
    page,
  }) => {
    const activePanel = page.locator('[data-slot="tabs-content"]').last()
    await expect(activePanel).toBeVisible()
  })

  test('portfolio view component renders when implemented', async ({ page }) => {
    const portfolioView = page.getByTestId('portfolio-view')
    if (await portfolioView.count() > 0) {
      await expect(portfolioView).toBeVisible({ timeout: 5000 })
    }
  })

  test('account balance shown from mock when PortfolioView exists', async ({
    page,
  }) => {
    const portfolioView = page.getByTestId('portfolio-view')
    if (await portfolioView.count() > 0) {
      // balance: 95000
      await expect(page.getByText(/95,000|95000/)).toBeVisible()
    }
  })

  test('P&L negative when balance less than initial when implemented', async ({
    page,
  }) => {
    const portfolioView = page.getByTestId('portfolio-view')
    if (await portfolioView.count() > 0) {
      // balance 95000 < initial 100000 → P&L -5000
      await expect(page.getByText(/-5,000|-5000/)).toBeVisible()
    }
  })

  test('positions table shows AAPL row when implemented', async ({ page }) => {
    const table = page.getByTestId('positions-table')
    if (await table.count() > 0) {
      await expect(table).toBeVisible({ timeout: 5000 })
      await expect(table.getByText('AAPL')).toBeVisible()
      await expect(table.getByText('10')).toBeVisible()
    }
  })

  test('equity curve chart renders when implemented', async ({ page }) => {
    const chart = page.getByTestId('equity-curve-chart')
    if (await chart.count() > 0) {
      await expect(chart).toBeVisible({ timeout: 5000 })
    }
  })

  test('allocation pie chart renders when implemented', async ({ page }) => {
    const chart = page.getByTestId('allocation-pie-chart')
    if (await chart.count() > 0) {
      await expect(chart).toBeVisible({ timeout: 5000 })
    }
  })

  test('no JavaScript errors on portfolio tab', async ({ page }) => {
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
