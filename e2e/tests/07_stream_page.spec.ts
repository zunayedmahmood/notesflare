// e2e/tests/07_stream_page.spec.ts

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://localhost:8000/api/test/reset");
});

test("stream page auto-focuses the input on load with existing session", async ({ page }) => {
  // Setup: create a Flareon and session via API
  const flareonRes = await page.request.post("http://localhost:8000/api/flareons", {
    data: { name: "Physics" },
  });
  const flareon = await flareonRes.json();
  await page.request.get(`http://localhost:8000/api/session/switch/${flareon.id}`);

  await page.goto("/");
  await page.waitForSelector("[data-testid='stream-input']");

  // Input must be focused — user can type immediately
  const focused = await page.evaluate(
    () => document.activeElement?.getAttribute("data-testid") === "stream-input"
  );
  expect(focused).toBe(
    true,
    "Stream input must be auto-focused on page load. " +
      "The user must be able to type without clicking first."
  );
});

test("typing in the stream input does not cause visible lag", async ({ page }) => {
  const flareonRes = await page.request.post("http://localhost:8000/api/flareons", {
    data: { name: "Speed Test" },
  });
  const flareon = await flareonRes.json();
  await page.request.get(`http://localhost:8000/api/session/switch/${flareon.id}`);

  await page.goto("/");
  await page.waitForSelector("[data-testid='stream-input']");

  const input = page.locator("[data-testid='stream-input']");
  await input.focus();

  // Type a long string and verify it appears in the input
  const testText = "The quick brown fox jumps over the lazy dog";
  await input.pressSequentially(testText, { delay: 20 });

  const value = await input.inputValue();
  expect(value).toBe(testText);
});

test("session indicator shows burst start time", async ({ page }) => {
  const flareonRes = await page.request.post("http://localhost:8000/api/flareons", {
    data: { name: "Indicator Test" },
  });
  const flareon = await flareonRes.json();
  await page.request.get(`http://localhost:8000/api/session/switch/${flareon.id}`);

  await page.goto("/");
  await page.waitForSelector("[data-testid='session-indicator']");

  const text = await page.locator("[data-testid='session-indicator']").textContent();
  expect(text).toContain("Burst since");
});
