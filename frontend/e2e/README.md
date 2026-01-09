# E2E Tests for nozzly.app

This directory contains end-to-end tests for the nozzly.app frontend using Playwright.

## Overview

E2E tests verify complete user workflows by automating real browser interactions. Unlike unit or component tests, E2E tests ensure that the entire application stack (frontend + backend) works correctly together.

## Setup

### Prerequisites

- Node.js 18+
- Running backend API (port 8000)
- Test user account in the database

### Installation

```bash
# Install Playwright browsers (first time only)
npx playwright install

# Copy environment configuration
cp .env.e2e.example .env.e2e

# Edit .env.e2e with actual test credentials
```

### Configuration

Edit `.env.e2e` with your test configuration:

```bash
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=testpassword
PLAYWRIGHT_BASE_URL=http://localhost:5173
```

**Important**: Use a dedicated test account, not your production credentials.

## Running Tests

### Run all E2E tests

```bash
npm run test:e2e
```

### Run tests with UI (interactive mode)

```bash
npm run test:e2e:ui
```

### Run tests in headed mode (see browser)

```bash
npm run test:e2e:headed
```

### Debug a specific test

```bash
npm run test:e2e:debug
```

### Run a specific test file

```bash
npm run test:e2e production-run-auto-population.spec.ts
```

### View test report

```bash
npm run test:e2e:report
```

## Test Coverage

### Production Run Auto-Population

**File**: `production-run-auto-population.spec.ts`

Tests the complete workflow for creating a production run with auto-populated materials from Model BOM:

1. **Main Flow Test**: Create model → Select in wizard → Verify suggestions → Apply suggestions → Submit run
2. **Low Inventory Warning**: Verify warnings when spool has insufficient inventory
3. **Inactive Spool Warning**: Verify warnings when spool is depleted/inactive
4. **Multi-Model Grouping**: Verify materials are correctly grouped when multiple models share spools

**What It Verifies**:
- ✅ Production defaults are fetched when model selected
- ✅ Suggested materials appear in Step 3 with correct weights
- ✅ Weights are scaled by quantity (e.g., 50g * 10 items = 500g)
- ✅ "Apply All Suggestions" button pre-fills materials
- ✅ Materials show inventory warnings (low/inactive)
- ✅ Per-model breakdown visible for shared spools
- ✅ Production run successfully created with auto-populated data

## Writing New Tests

### Test Structure

```typescript
import { test, expect } from '@playwright/test'

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Login, navigate to starting point
  })

  test('should do something', async ({ page }) => {
    // Arrange: Set up test data
    // Act: Perform user actions
    // Assert: Verify expected outcomes
  })

  test.afterEach(async ({ page }) => {
    // Cleanup: Delete test data
  })
})
```

### Best Practices

1. **Test Isolation**: Each test should be independent
2. **Cleanup**: Always delete test data in `afterEach`
3. **Wait for State**: Use `waitForLoadState('networkidle')` for API calls
4. **Explicit Waits**: Use `waitForURL`, `waitForSelector` instead of `setTimeout`
5. **Data-Testid**: Prefer `[data-testid="..."]` selectors over text
6. **Unique Test Data**: Use timestamps in test data to avoid conflicts

### Selectors Priority

1. `[data-testid="unique-id"]` (best - stable)
2. `button[type="submit"]` (good - semantic)
3. `text=Exact Text` (okay - fragile to i18n)
4. `.css-class` (avoid - implementation detail)

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install Playwright
  run: npx playwright install --with-deps

- name: Run E2E Tests
  run: npm run test:e2e
  env:
    TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
    TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Troubleshooting

### Tests Timeout

- Check backend is running on port 8000
- Check frontend dev server is running on port 5173
- Increase timeout in `playwright.config.ts`

### Authentication Fails

- Verify credentials in `.env.e2e`
- Check test user exists in database
- Check login endpoint is working

### Selectors Not Found

- Run tests in headed mode: `npm run test:e2e:headed`
- Use Playwright Inspector: `npm run test:e2e:debug`
- Check if UI changed (update selectors)

### Flaky Tests

- Add explicit waits: `await page.waitForLoadState('networkidle')`
- Increase action timeouts
- Check for race conditions

## Test Data Management

### Database Seeding

For consistent E2E tests, seed the database with:
- Test user account
- Sample spools (various materials, colors)
- Sample material types

### Cleanup Strategy

- Tests create unique models using timestamps
- `afterEach` hook deletes created models
- Backend should cascade delete BOM materials

## Performance

### Parallel Execution

Playwright runs tests in parallel by default. Configure workers in `playwright.config.ts`:

```typescript
workers: process.env.CI ? 1 : undefined
```

### Test Sharding (CI)

Split tests across multiple machines:

```bash
npx playwright test --shard=1/3
npx playwright test --shard=2/3
npx playwright test --shard=3/3
```

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright Selectors](https://playwright.dev/docs/selectors)
- [Playwright Test API](https://playwright.dev/docs/api/class-test)

---

**Maintained by**: Jonathan Gill
**Last Updated**: December 14, 2025
