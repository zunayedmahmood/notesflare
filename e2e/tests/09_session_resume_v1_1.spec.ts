// e2e/tests/09_session_resume_v1_1.spec.ts

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://localhost:8000/api/test/reset");
});

test("first-time user sees EmptyState not stream input", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector("[data-testid='empty-state']");

  const emptyVisible = await page.locator("[data-testid='empty-state']").isVisible();
  const streamVisible = await page
    .locator("[data-testid='stream-input']")
    .isVisible()
    .catch(() => false);

  expect(emptyVisible).toBe(true, "First-time user must see EmptyState.");
  expect(streamVisible).toBe(false, "First-time user must not see stream input.");
});

test("session/resume is called on startup (not /api/state)", async ({ page }) => {
  const calls: string[] = [];
  await page.route("**/api/**", (route) => {
    calls.push(route.request().url());
    route.continue();
  });

  await page.goto("/");
  await page.waitForTimeout(500);

  const calledResume = calls.some((url) => url.includes("/api/session/resume"));
  const calledOldState = calls.some((url) => url.endsWith("/api/state"));

  expect(calledResume).toBe(
    true,
    "V1.1 startup must call /api/session/resume. " + `Calls made: ${calls.join(", ")}`
  );
  expect(calledOldState).toBe(
    false,
    "V1.1 startup must NOT call the V1 /api/state endpoint. " +
      `Calls made: ${calls.join(", ")}`
  );
});

test("switching Flareons calls session/switch not flareons/{id}", async ({
  page,
  request,
}) => {
  await request.post("http://localhost:8000/api/flareons", { data: { name: "Alpha" } });
  await request.post("http://localhost:8000/api/flareons", { data: { name: "Beta" } });

  const calls: string[] = [];
  await page.route("**/api/**", (route) => {
    calls.push(route.request().url());
    route.continue();
  });

  await page.goto("/");
  await page.waitForSelector("[data-testid='flareon-item']");
  await page.locator("[data-testid='flareon-item']").first().click();
  await page.waitForTimeout(300);

  const calledSwitch = calls.some((url) => url.includes("/api/session/switch/"));
  expect(calledSwitch).toBe(
    true,
    "Clicking a Flareon in the sidebar must call /api/session/switch/{id}. " +
      `Calls made: ${calls.join(", ")}`
  );
});
