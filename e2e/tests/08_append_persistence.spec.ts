// e2e/tests/08_append_persistence.spec.ts

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://localhost:8000/api/test/reset");
});

test("typed content is sent to /api/burst/append after 1 second pause", async ({
  page,
  request,
}) => {
  const flareonRes = await request.post("http://localhost:8000/api/flareons", {
    data: { name: "Append E2E" },
  });
  const flareon = await flareonRes.json();
  await request.get(`http://localhost:8000/api/session/switch/${flareon.id}`);

  // Capture the append request
  let appendPayload: { burst_id: number; text: string } | null = null;
  await page.route("**/api/burst/append", async (route) => {
    const body = route.request().postDataJSON();
    appendPayload = body;
    await route.continue();
  });

  await page.goto("/");
  await page.waitForSelector("[data-testid='stream-input']");

  await page.locator("[data-testid='stream-input']").pressSequentially("Hello persistence");

  // Wait longer than the 1s debounce
  await page.waitForTimeout(1500);

  expect(appendPayload).not.toBeNull();
  expect(appendPayload!.text).toBe("Hello persistence");
  expect(typeof appendPayload!.burst_id).toBe("number");
});

test("content survives page reload via session resume", async ({ page, request }) => {
  const flareonRes = await request.post("http://localhost:8000/api/flareons", {
    data: { name: "Survive Reload" },
  });
  const flareon = await flareonRes.json();
  await request.get(`http://localhost:8000/api/session/switch/${flareon.id}`);

  await page.goto("/");
  await page.waitForSelector("[data-testid='stream-input']");

  await page.locator("[data-testid='stream-input']").pressSequentially("Persistent thought");
  // Wait for autosave
  await page.waitForTimeout(1500);

  // Reload page
  await page.reload();
  await page.waitForSelector("[data-testid='stream-input']");

  const value = await page.locator("[data-testid='stream-input']").inputValue();
  expect(value).toBe(
    "Persistent thought",
    "After reload, stream input must show the previously typed and saved content. " +
      `Got: '${value}'. ` +
      "This tests the full append → reconstruct → session resume pipeline."
  );
});

test("multiple typing sessions accumulate content correctly", async ({
  page,
  request,
}) => {
  const flareonRes = await request.post("http://localhost:8000/api/flareons", {
    data: { name: "Multi-Session" },
  });
  const flareon = await flareonRes.json();
  await request.get(`http://localhost:8000/api/session/switch/${flareon.id}`);

  await page.goto("/");
  await page.waitForSelector("[data-testid='stream-input']");

  await page.locator("[data-testid='stream-input']").pressSequentially("First part");
  await page.waitForTimeout(1500); // first save

  await page.locator("[data-testid='stream-input']").pressSequentially(" second part");
  await page.waitForTimeout(1500); // second save

  // Verify backend has full content
  const resumeRes = await request.get("http://localhost:8000/api/session/resume");
  const resume = await resumeRes.json();

  expect(resume.stream_content).toBe(
    "First part second part",
    `[E2E] stream_content after two saves must be the concatenation of both deltas. ` +
      `Got: '${resume.stream_content}'`
  );
});
