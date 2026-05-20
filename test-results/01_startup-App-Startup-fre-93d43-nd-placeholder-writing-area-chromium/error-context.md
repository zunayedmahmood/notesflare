# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: 01_startup.spec.ts >> App Startup >> fresh start shows empty sidebar and placeholder writing area
- Location: e2e/tests/01_startup.spec.ts:5:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('[data-testid="sidebar"]')
Expected: visible
Timeout: 2000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 2000ms
  - waiting for locator('[data-testid="sidebar"]')

```

```yaml
- alert
```

# Test source

```ts
  1  | // e2e/tests/01_startup.spec.ts
  2  | import { test, expect } from '../fixtures/app.fixture';
  3  | 
  4  | test.describe('App Startup', () => {
  5  |   test('fresh start shows empty sidebar and placeholder writing area', async ({ page }) => {
  6  |     await page.goto('/');
  7  | 
  8  |     const sidebar = page.locator('[data-testid="sidebar"]');
> 9  |     await expect(sidebar).toBeVisible({
     |                           ^ Error: expect(locator).toBeVisible() failed
  10 |       timeout: 2000,
  11 |     });
  12 | 
  13 |     const flareonItems = page.locator('[data-testid="flareon-item"]');
  14 |     await expect(flareonItems).toHaveCount(0, {
  15 |       timeout: 2000,
  16 |     });
  17 | 
  18 |     const placeholder = page.locator('[data-testid="writing-area-placeholder"]');
  19 |     await expect(placeholder).toBeVisible();
  20 |     await expect(placeholder).toContainText('Select a Flareon');
  21 |   });
  22 | 
  23 |   test('writing area is not visible without a selected Flareon', async ({ page }) => {
  24 |     await page.goto('/');
  25 | 
  26 |     const textarea = page.locator('[data-testid="writing-textarea"]');
  27 |     await expect(textarea).not.toBeVisible();
  28 |   });
  29 | 
  30 |   test('app loads within 2 seconds', async ({ page }) => {
  31 |     const start = Date.now();
  32 |     await page.goto('/');
  33 |     await page.locator('[data-testid="sidebar"]').waitFor({ state: 'visible' });
  34 |     const elapsed = Date.now() - start;
  35 | 
  36 |     expect(elapsed).toBeLessThan(2000);
  37 |   }, {
  38 |     annotation: {
  39 |       type: 'performance',
  40 |       description: `[E2E Startup] App did not render within 2 seconds.
  41 |   This violates the core product performance requirement.
  42 |   Check: Is the backend responding? Is the Next.js build optimized?
  43 |   Run: curl http://localhost:8000/api/health to verify backend is up.`
  44 |     }
  45 |   });
  46 | });
  47 | 
```