// e2e/fixtures/app.fixture.ts
/**
 * Shared fixture for all E2E tests.
 * Provides a fresh test database before each test by calling a reset endpoint
 * (available only in test mode) and ensures the backend is running.
 */

import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  page: async ({ page }, use) => {
    // Wipe the test database before each E2E test
    await page.request.post('http://localhost:8000/api/test/reset', {
      failOnStatusCode: true,
    }).catch(() => {
      throw new Error(
        '[E2E Fixture] Could not reset test database.\n' +
        '  POST http://localhost:8000/api/test/reset returned non-200.\n' +
        '  This endpoint must exist in the backend when NOTESFLARE_ENV=test.\n' +
        '  Fix: Add a /api/test/reset route in routes.py that drops and re-creates\n' +
        '  all tables. Guard it: if os.getenv("NOTESFLARE_ENV") != "test": raise 403.'
      );
    });

    await use(page);
  },
});

export { expect };
