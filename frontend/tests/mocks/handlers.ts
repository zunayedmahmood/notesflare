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

  // V1.1 endpoints
  http.get(`${BASE}/api/session/resume`, () =>
    HttpResponse.json({
      has_session: false,
      flareon: null,
      burst_id: null,
      stream_content: '',
      started_at: null,
    })
  ),

  http.get(`${BASE}/api/session/switch/:id`, ({ params }) => {
    const id = Number(params.id);
    return HttpResponse.json({
      flareon: { id, name: 'Test Flareon', created_at: '2025-01-15T10:00:00', last_opened_at: null },
      burst_id: 1,
      stream_content: '',
      started_at: '2025-01-15T10:00:00',
    });
  }),

  http.post(`${BASE}/api/burst/append`, () =>
    HttpResponse.json({ success: true, sequence_number: 0 })
  ),
];

// ─── V1.2 Formatting Handlers ────────────────────────────────────────────────

export const formattingHandlers = [
  http.post("http://127.0.0.1:8000/api/format/burst", () =>
    HttpResponse.json({
      burst_id: 1,
      lines: [
        {
          line_id: "line-001",
          line_index: 0,
          raw_line: "first line of content here",
          formatted_line: "first line of content here",
          status: "untouched",
          checksum: "abc123",
        },
      ],
      diffs: [
        {
          diff_id: "diff-001",
          line_id: "line-001",
          operation: "insert_paragraph_break",
          status: "pending",
          raw_before: "first line of content here",
          formatted_after: "\nfirst line of content here",
        },
      ],
      diff_count: 1,
      processed_at: new Date().toISOString(),
    })
  ),

  http.post("http://127.0.0.1:8000/api/format/diff/accept", () =>
    HttpResponse.json({
      diff_id: "diff-001",
      status: "accepted",
      line_id: "line-001",
      updated_formatted_line: "\nfirst line of content here",
    })
  ),

  http.post("http://127.0.0.1:8000/api/format/diff/reject", () =>
    HttpResponse.json({
      diff_id: "diff-001",
      status: "rejected",
      line_id: "line-001",
      updated_formatted_line: "first line of content here",
    })
  ),

  http.post("http://127.0.0.1:8000/api/format/diff/accept-all", () =>
    HttpResponse.json({ updated_count: 1, diffs: [] })
  ),

  http.post("http://127.0.0.1:8000/api/format/diff/reject-all", () =>
    HttpResponse.json({ updated_count: 1, diffs: [] })
  ),

  http.get("http://127.0.0.1:8000/api/format/burst/:burst_id", () =>
    HttpResponse.json({
      burst_id: 1,
      has_formatting: true,
      lines: [],
      formatted_text: "\nfirst line of content here",
      raw_text: "first line of content here",
    })
  ),
];

export const server = setupServer(...defaultHandlers, ...formattingHandlers);


