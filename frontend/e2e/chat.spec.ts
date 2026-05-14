import { test, expect } from '@playwright/test'
import { mockBackend, loginViaCookie } from './helpers'

test.describe('Chat Widget', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaCookie(page)
    await mockBackend(page)

    // Mock the chat endpoint
    await page.route('**/api/chat/message', (route) =>
      route.fulfill({
        status: 200,
        json: { reply: 'RSI at 55.2 indicates neutral momentum. The trending regime suggests momentum strategies may be effective.' },
      }),
    )

    await page.goto('/dashboard')
  })

  test('chat toggle opens and closes the panel', async ({ page }) => {
    const toggle = page.getByTestId('chat-toggle')
    await expect(toggle).toBeVisible()

    // Panel should not be visible initially
    await expect(page.getByTestId('chat-panel')).not.toBeVisible()

    // Click to open
    await toggle.click()
    await expect(page.getByTestId('chat-panel')).toBeVisible()

    // Click to close
    await toggle.click()
    await expect(page.getByTestId('chat-panel')).not.toBeVisible()
  })

  test('sending a message shows response', async ({ page }) => {
    // Open chat
    await page.getByTestId('chat-toggle').click()
    await expect(page.getByTestId('chat-panel')).toBeVisible()

    // Type and send a message
    const input = page.getByTestId('chat-input')
    await input.fill('What does the RSI indicate?')
    await page.getByTestId('chat-send').click()

    // Verify user message appears
    const userMsg = page.getByTestId('chat-message-user')
    await expect(userMsg).toBeVisible()

    // Verify assistant response appears
    const botMsg = page.getByTestId('chat-message-assistant')
    await expect(botMsg).toBeVisible()
    await expect(botMsg).toContainText('RSI')
  })

  test('model selector dropdown works', async ({ page }) => {
    await page.getByTestId('chat-toggle').click()
    const selector = page.getByTestId('chat-model-selector')
    await expect(selector).toBeVisible()

    // Should have 3 model options
    const options = selector.locator('option')
    await expect(options).toHaveCount(3)

    // Change model selection
    await selector.selectOption('deepseek/deepseek-r1:free')
    await expect(selector).toHaveValue('deepseek/deepseek-r1:free')
  })

  test('chat sends context with active section', async ({ page }) => {
    let capturedBody: Record<string, unknown> | null = null

    // Intercept to capture the request body
    await page.route('**/api/chat/message', async (route) => {
      const request = route.request()
      capturedBody = JSON.parse(request.postData() || '{}') as Record<string, unknown>
      await route.fulfill({
        status: 200,
        json: { reply: 'Test response' },
      })
    })

    // Switch to Market Scanner via sidebar
    await page.getByTestId('sidebar-nav').getByText('Market Scanner').click()

    // Open chat and send message
    await page.getByTestId('chat-toggle').click()
    await page.getByTestId('chat-input').fill('What signals are active?')
    await page.getByTestId('chat-send').click()

    // Wait for the request to be captured
    await page.waitForTimeout(500)

    // Verify context includes the active section
    expect(capturedBody).not.toBeNull()
    expect((capturedBody?.context as Record<string, unknown>)?.active_tab).toBe('scanner')
  })
})
