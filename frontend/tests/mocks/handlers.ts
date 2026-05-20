// frontend/tests/mocks/handlers.ts
/**
 * MSW mock handlers that simulate the Python backend.
 * Tests import and override these handlers to simulate different backend states.
 */

import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

const BASE = 'http://localhost:8000';

export const defaultHandlers = [
  http.get(`${BASE}/api/health`, () =>
    HttpResponse.json({ status: 'ok' })
  ),

  http.get(`${BASE}/api/state`, () =>
    HttpResponse.json({
      last_opened_flareon_id: null,
      last_opened_burst_id: null,
    })
  ),

  http.get(`${BASE}/api/flareons`, () =>
    HttpResponse.json({ flareons: [] })
  ),

  http.post(`${BASE}/api/flareons`, async ({ request }) => {
    const body = await request.json() as { name: string };
    return HttpResponse.json(
      { id: 1, name: body.name, created_at: '2025-01-15T10:00:00', last_opened_at: null },
      { status: 201 }
    );
  }),

  http.get(`${BASE}/api/flareons/:id`, ({ params }) => {
    const id = Number(params.id);
    return HttpResponse.json({
      flareon: { id, name: 'Test Flareon', created_at: '2025-01-15T10:00:00', last_opened_at: null },
      bursts: [
        { id: 1, flareon_id: id, started_at: '2025-01-15T10:00:00', content: '' }
      ],
      active_burst_id: 1,
    });
  }),

  http.post(`${BASE}/api/save`, () =>
    HttpResponse.json({ success: true, burst_entry_id: 1 })
  ),
];

export const server = setupServer(...defaultHandlers);
