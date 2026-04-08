import { test, expect } from '@playwright/test'
import { mockBackend } from './helpers'

test.describe('Authentication', () => {
  test('landing page is public and shows hero text', async ({ page }) => {
    await page.goto('/')
    await expect(
      page.getByText(/AI-Powered Trading Intelligence/i),
    ).toBeVisible()
  })

  test('landing page feature cards render', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/Real-Time Signal Feed/i)).toBeVisible()
    await expect(page.getByText(/Candlestick Charts/i)).toBeVisible()
    await expect(page.getByText(/Paper Trading/i)).toBeVisible()
    await expect(page.getByText(/Backtest Strategies/i)).toBeVisible()
    await expect(page.getByText(/Market Regime Detection/i)).toBeVisible()
    await expect(page.getByText(/Risk Management/i)).toBeVisible()
  })

  test('landing page CTA button navigates to /login', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /Start Trading/i }).click()
    await expect(page).toHaveURL(/\/login/)
  })

  test('unauthenticated /dashboard redirects to /login', async ({ page }) => {
    await page.route('**/auth/me', (route) =>
      route.fulfill({
        status: 401,
        json: { detail: 'Not authenticated' },
      }),
    )
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })

  test('login page renders form with username and password fields', async ({
    page,
  }) => {
    await page.goto('/login')
    await expect(page.getByLabel(/username/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(
      page.getByRole('button', { name: /sign in/i }),
    ).toBeVisible()
  })

  test('login with valid credentials redirects to /dashboard', async ({
    page,
  }) => {
    // Mock auth/me to return 401 so user stays on login page
    await page.route('**/auth/me', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Not authenticated' } }),
    )
    await page.route('**/auth/login', (route) =>
      route.fulfill({ status: 200, json: { status: 'ok' } }),
    )

    await page.goto('/login')
    // Wait for form to be ready (isLoading=false after checkAuth resolves)
    await expect(page.getByLabel(/username/i)).toBeVisible({ timeout: 8000 })
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('testpassword')
    await page.getByRole('button', { name: /sign in/i }).click()
    // After loginUser() succeeds, setAuthenticated() is called → navigate('/dashboard')
    // PrivateRoute will call checkAuth() which hits /auth/me (401), but isAuthenticated
    // is already true in the store from setAuthenticated, so checkAuth is skipped
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 8000 })
  })

  test('login with wrong credentials shows error message', async ({
    page,
  }) => {
    await page.route('**/auth/login', (route) =>
      route.fulfill({
        status: 401,
        json: { detail: 'Invalid credentials' },
      }),
    )

    await page.goto('/login')
    await page.getByLabel(/username/i).fill('admin')
    await page.getByLabel(/password/i).fill('wrongpassword')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText(/invalid credentials/i)).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('logout redirects to /login', async ({ page }) => {
    await mockBackend(page)
    await page.goto('/dashboard')

    await page.getByRole('button', { name: /logout/i }).click()
    await expect(page).toHaveURL(/\/login/)
  })
})
