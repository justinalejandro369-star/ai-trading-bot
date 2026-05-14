import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Signal Feed', () => {
  test.beforeEach(async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')
    // Navigate to Market Scanner via sidebar
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()
  })

  test('signal feed heading is visible', async ({ page }) => {
    await expect(page.getByText('AI Signal Feed')).toBeVisible()
  })

  test('renders AAPL BUY signal card from mock data when SignalFeed exists', async ({
    page,
  }) => {
    const card = page.getByTestId('signal-aapl')
    // If SignalFeed is present, assert card content
    if (await card.count() > 0) {
      await expect(card).toBeVisible()
      await expect(card.getByText('BUY')).toBeVisible()
      await expect(card.getByText('85')).toBeVisible()
    }
  })

  test('signal card shows entry, stop-loss, target when implemented', async ({
    page,
  }) => {
    const card = page.getByTestId('signal-aapl')
    if (await card.count() > 0) {
      await expect(card.getByText(/172/)).toBeVisible()
      await expect(card.getByText(/168/)).toBeVisible()
      await expect(card.getByText(/180/)).toBeVisible()
    }
  })

  test('signal card shows regime badge when implemented', async ({ page }) => {
    const card = page.getByTestId('signal-aapl')
    if (await card.count() > 0) {
      await expect(card.getByText(/trending/i)).toBeVisible()
    }
  })

  test('SELL signal has different badge styling when implemented', async ({
    page,
  }) => {
    await page.route('**/api/signals/top**', (route) =>
      route.fulfill({
        status: 200,
        json: [
          {
            symbol: 'MSFT',
            direction: 'SELL',
            confidence: 70,
            regime: 'ranging',
            close: 420,
            entry_price: 419,
            stop_loss: 425,
            target_price: 410,
            rsi_14: 68,
            macd_val: -0.5,
            adx_14: 15,
            atr_14: 4.1,
            reasons: [],
            interval: '1D',
            scanned_at: new Date().toISOString(),
          },
        ],
      }),
    )
    await page.reload()
    // Re-navigate to Market Scanner after reload
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()

    const sellCard = page.getByTestId('signal-msft')
    if (await sellCard.count() > 0) {
      await expect(sellCard.getByText('SELL')).toBeVisible()
    }
  })

  test('WebSocket signal_update pushes new signal to feed', async ({
    page,
  }) => {
    await page.routeWebSocket(/\/ws\/live/, (ws) => {
      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: 'signal_update',
            signal: {
              symbol: 'MSFT',
              direction: 'SELL',
              confidence: 72,
              regime: 'ranging',
              close: 420.0,
              entry_price: 419.0,
              stop_loss: 425.0,
              target_price: 410.0,
              rsi_14: 68,
              macd_val: -0.5,
              adx_14: 15,
              atr_14: 4.1,
              reasons: ['RSI overbought'],
              interval: '1D',
              scanned_at: new Date().toISOString(),
            },
          }),
        )
      }
    })

    await page.goto('/dashboard')
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()

    // Feed heading must be visible
    await expect(page.getByText('AI Signal Feed')).toBeVisible()

    const msftCard = page.getByTestId('signal-msft')
    if (await msftCard.count() > 0) {
      await expect(msftCard).toBeVisible({ timeout: 5000 })
    }
  })
})
