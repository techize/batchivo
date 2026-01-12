import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright Configuration for batchivo.com E2E Tests
 *
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',

  /* Run tests in files in parallel - disabled to prevent registration rate limiting */
  fullyParallel: false,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry failed tests (helps with rate limiting flakiness) */
  retries: process.env.CI ? 2 : 1,

  /* Single worker to prevent registration rate limiting */
  workers: 1,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    /* Default to production for E2E tests; use PLAYWRIGHT_BASE_URL=http://localhost:5173 for local */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://www.batchivo.com',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  /* Run local dev server only when testing locally (set PLAYWRIGHT_BASE_URL=http://localhost:5173) */
  webServer: process.env.PLAYWRIGHT_BASE_URL?.includes('localhost')
    ? {
        command: `VITE_API_URL=${process.env.PLAYWRIGHT_API_URL || 'https://api.batchivo.com'} npm run dev`,
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
        stdout: 'ignore',
        stderr: 'pipe',
      }
    : undefined,
})
