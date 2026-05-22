// e2e/tests/01_startup.spec.ts
import { test, expect } from '../fixtures/app.fixture';

test.describe('App Startup', () => {
  test('fresh start shows empty sidebar and placeholder writing area', async ({ page }) => {
    await page.goto('/');

    const sidebar = page.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible({
      timeout: 2000,
    });

    const flareonItems = page.locator('[data-testid="flareon-item"]');
    await expect(flareonItems).toHaveCount(0, {
      timeout: 2000,
    });

    const placeholder = page.locator('[data-testid="empty-state"]');
    await expect(placeholder).toBeVisible();
    await expect(placeholder).toContainText('Select a Flareon');
  });

  test('writing area is not visible without a selected Flareon', async ({ page }) => {
    await page.goto('/');

    const streamInput = page.locator('[data-testid="stream-input"]');
    await expect(streamInput).not.toBeVisible();
  });

  test('app loads within 2 seconds', async ({ page }) => {
    const start = Date.now();
    await page.goto('/');
    await page.locator('[data-testid="sidebar"]').waitFor({ state: 'visible' });
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(2000);
  }, {
    annotation: {
      type: 'performance',
      description: `[E2E Startup] App did not render within 2 seconds.
  This violates the core product performance requirement.
  Check: Is the backend responding? Is the Next.js build optimized?
  Run: curl http://localhost:8000/api/health to verify backend is up.`
    }
  });
});
