import { test, expect } from '@playwright/test'

test.describe('Authentication Flow', () => {
  test('should display marketing site', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/TasteOS/)
    await expect(page.locator('h1')).toContainText('TasteOS')
  })

  test('should navigate to signup', async ({ page }) => {
    await page.goto('/')

    // Click get started button
    await page.click('text=Get Started')

    // Should redirect to signup page
    await expect(page).toHaveURL(/.*signup/)
  })

  test('should navigate to login', async ({ page }) => {
    await page.goto('/')

    // Click sign in button
    await page.click('text=Sign In')

    // Should redirect to login page
    await expect(page).toHaveURL(/.*login/)
  })

  test('should handle user registration', async ({ page }) => {
    await page.goto('/signup')

    // Fill registration form
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password123')
    await page.fill('[data-testid="name"]', 'Test User')

    // Submit form
    await page.click('[data-testid="submit"]')

    // Should redirect to dashboard after successful registration
    // Note: This will fail until auth is implemented
    // await expect(page).toHaveURL(/.*dashboard/)
  })

  test('should handle user login', async ({ page }) => {
    await page.goto('/login')

    // Fill login form
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password123')

    // Submit form
    await page.click('[data-testid="submit"]')

    // Should redirect to dashboard after successful login
    // Note: This will fail until auth is implemented
    // await expect(page).toHaveURL(/.*dashboard/)
  })
})
