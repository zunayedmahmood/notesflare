// e2e/tests/03_autosave.spec.ts
import { test, expect } from '../fixtures/app.fixture';

test.describe('Autosave', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-testid="new-flareon-button"]').click();
    await page.locator('[data-testid="new-flareon-input"]').fill('Autosave Test');
    await page.keyboard.press('Enter');
    await page.locator('[data-testid="stream-input"]').waitFor({ state: 'visible' });
  });

  test('content is persisted 1 second after typing stops', async ({ page, request }) => {
    const streamInput = page.locator('[data-testid="stream-input"]');
    await streamInput.click();
    await streamInput.pressSequentially('Test content for autosave');

    // Wait 1.5 seconds for debounce + HTTP save to complete
    await page.waitForTimeout(1500);

    // Query the backend directly to verify DB write
    const response = await request.get('http://localhost:8000/api/flareons');
    const data = await response.json();
    const flareon = data.flareons.find((f: { name: string }) => f.name === 'Autosave Test');

    expect(flareon).toBeDefined();

    const detail = await request.get(`http://localhost:8000/api/flareons/${flareon.id}`);
    const detailData = await detail.json();
    const activeBurst = detailData.bursts.find(
      (b: { id: number }) => b.id === detailData.active_burst_id
    );

    expect(activeBurst?.content).toBe('Test content for autosave');
  }, {
    annotation: {
      type: 'performance',
      description: `[E2E Autosave] Content not found in database after typing + 1.5s wait.
  Possible causes:
  1. useAutosave debounce timer is not 1000ms
  2. POST /api/save is failing silently (check Network tab in browser devtools)
  3. storage_service.save_content is not committing (missing db.commit())
  4. The burst_id passed to /api/save is null (Flareon not properly opened)
  Debug: Open browser devtools Network tab and look for POST /api/save requests.`
    }
  });

  test('no save indicator appears in the UI during typing', async ({ page }) => {
    const streamInput = page.locator('[data-testid="stream-input"]');
    await streamInput.pressSequentially('Silent typing');

    // Check for any save-related text in the entire DOM
    const saveText = page.locator('text=/saving|saved|sync/i');
    await expect(saveText).toHaveCount(0);
  });
});
