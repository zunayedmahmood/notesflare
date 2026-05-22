// e2e/tests/04_session_restore.spec.ts
import { test, expect } from '../fixtures/app.fixture';

test.describe('Session Restore', () => {
  test('reopening app restores last Flareon and content', async ({ page }) => {
    await page.goto('/');

    // Create flareon and write content
    await page.locator('[data-testid="new-flareon-button"]').click();
    await page.locator('[data-testid="new-flareon-input"]').fill('Restore Me');
    await page.keyboard.press('Enter');
    const streamInput = page.locator('[data-testid="stream-input"]');
    await streamInput.waitFor({ state: 'visible' });
    await streamInput.pressSequentially('This should survive a reload');
    await page.waitForTimeout(1500); // let autosave fire

    // Simulate app restart by navigating away and back
    await page.goto('about:blank');
    await page.goto('/');

    // Verify session restored
    const restoredFlareon = page.locator('[data-testid="flareon-item"].active');
    await expect(restoredFlareon).toContainText('Restore Me');

    const restoredStreamInput = page.locator('[data-testid="stream-input"]');
    await expect(restoredStreamInput).toHaveValue('This should survive a reload');
  }, {
    annotation: {
      type: 'performance',
      description: `[E2E Session Restore] Content or active Flareon not restored on reload.
  Check:
  1. GET /api/state returns the correct last_opened_flareon_id after typing
  2. useSession.initSession() correctly calls GET /api/state then GET /api/flareons/{id}
  3. The textarea value is set from the active burst's content on Flareon open
  4. storage_service.update_app_state is called inside the GET /api/flareons/{id} route handler`
    }
  });
});
