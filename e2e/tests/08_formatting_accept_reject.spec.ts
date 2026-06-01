// e2e/tests/08_formatting_accept_reject.spec.ts

import { test, expect } from "../fixtures/app.fixture";

test.describe("V1.2 Formatting — End-To-End Journey", () => {
  test("Can format content, accept changes, and toggle formatted state on the archive timeline", async ({ page }) => {
    // 1. Load stream page
    await page.goto("/");
    await page.waitForSelector('[data-testid="new-flareon-button"]');

    // 2. Click the new-flareon-button to show the input field
    await page.click('[data-testid="new-flareon-button"]');
    await page.waitForSelector('[data-testid="new-flareon-input"]');

    // 3. Create a new Flareon to ensure clean isolation
    await page.fill('[data-testid="new-flareon-input"]', "Formatting E2E Flareon");
    await page.keyboard.press("Enter");
    
    // Now wait for the writing area to become active
    await page.waitForSelector('[data-testid="stream-input"]');

    // 4. Type text that will trigger structural formatting (e.g. list parsing)
    const streamInput = page.locator('[data-testid="stream-input"]');
    await streamInput.click();
    await streamInput.fill("* first formatting list line\n* second formatting list line");

    // 5. Wait for autosave to fire and persist to the database
    await page.waitForTimeout(1500);

    // 6. Trigger formatting pipeline
    const formatBtn = page.locator('[data-testid="format-button"]');
    await expect(formatBtn).toBeEnabled();
    await formatBtn.click();

    // 7. Wait for diff review panel to slide open and render
    const panel = page.locator('[data-testid="diff-review-panel"]');
    await expect(panel).toBeVisible({ timeout: 5000 });

    // 8. Verify pending diff counts
    await expect(page.locator('[data-testid="accept-all-btn"]')).toBeVisible();

    // 9. Accept all changes
    await page.click('[data-testid="accept-all-btn"]');

    // 10. Close diff review panel
    await page.click('[data-testid="diff-panel-close"]');
    await expect(panel).not.toBeVisible();

    // 11. Navigate to the archive page for this Flareon via Client-Side Navigation
    const archiveBtn = page.locator('[data-testid="nav-archive"]');
    await expect(archiveBtn).toBeVisible();
    await archiveBtn.click();

    // Wait for the timeline to render
    await page.waitForSelector('[data-testid="burst-timeline"]', { timeout: 5000 });

    // 12. Verify that the FormattedPreview and raw/formatted toggle buttons are present
    const preview = page.locator('[data-testid="formatted-preview"]');
    await expect(preview.first()).toBeVisible();

    const formattedBtn = page.locator('[data-testid="view-formatted-btn"]');
    await expect(formattedBtn).toBeVisible();

    const rawBtn = page.locator('[data-testid="view-raw-btn"]');
    await expect(rawBtn).toBeVisible();

    // 13. Toggle back and forth between raw and formatted content
    await formattedBtn.click();
    await page.waitForTimeout(200);
    await rawBtn.click();
  });
});
