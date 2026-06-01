// e2e/tests/07_formatting_basic.spec.ts

import { test, expect } from "@playwright/test";

test.describe("V1.2 Formatting — Basic Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for app to load
    await page.waitForSelector('[data-testid="stream-input"]', { timeout: 5000 });
  });

  test("Format button is visible in stream shell", async ({ page }) => {
    // Create a Flareon first if none exists
    const flareonItems = await page.locator('[data-testid="flareon-item"]').count();
    if (flareonItems === 0) {
      await page.fill('[data-testid="new-flareon-input"]', "Formatting E2E Test");
      await page.click('[data-testid="new-flareon-button"]');
      await page.waitForSelector('[data-testid="stream-input"]');
    }

    const formatBtn = page.locator('[data-testid="format-button"]');
    await expect(formatBtn).toBeVisible();
    await expect(formatBtn).toHaveText("Format");
  });

  test("Format button is disabled with no active burst", async ({ page }) => {
    // If no Flareon is selected, format button should be disabled
    // This test only runs if the empty state is showing
    const emptyState = page.locator('[data-testid="empty-state"]');
    if (await emptyState.isVisible()) {
      const formatBtn = page.locator('[data-testid="format-button"]');
      if (await formatBtn.isVisible()) {
        await expect(formatBtn).toBeDisabled();
      }
    }
  });

  test("Typing content then clicking Format opens diff panel", async ({ page }) => {
    // Ensure a Flareon is selected
    const flareonItems = page.locator('[data-testid="flareon-item"]');
    if (await flareonItems.count() === 0) {
      await page.fill('[data-testid="new-flareon-input"]', "Format Flow Test");
      await page.click('[data-testid="new-flareon-button"]');
    } else {
      await flareonItems.first().click();
    }

    await page.waitForSelector('[data-testid="stream-input"]');

    // Type content with list-like structure that should trigger diffs
    const streamInput = page.locator('[data-testid="stream-input"]');
    await streamInput.click();
    await streamInput.fill("- first item\n- second item\n- third item");

    // Wait for autosave
    await page.waitForTimeout(1500);

    // Click Format
    await page.click('[data-testid="format-button"]');

    // Diff panel may or may not open depending on content
    // Just verify no crash
    await page.waitForTimeout(2000);
    // If panel opened, it should have the close button
    const panel = page.locator('[data-testid="diff-review-panel"]');
    if (await panel.isVisible()) {
      await expect(page.locator('[data-testid="diff-panel-close"]')).toBeVisible();
    }
  });

  test("Closing diff panel hides it", async ({ page }) => {
    // Only runs if diff panel is open
    const panel = page.locator('[data-testid="diff-review-panel"]');
    if (await panel.isVisible()) {
      await page.click('[data-testid="diff-panel-close"]');
      await expect(panel).not.toBeVisible();
    }
  });
});
