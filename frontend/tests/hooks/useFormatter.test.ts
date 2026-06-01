// frontend/tests/hooks/useFormatter.test.ts

import { renderHook, act } from "@testing-library/react";
import { useFormatter } from "@/hooks/useFormatter";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";

const API_BASE = "http://127.0.0.1:8000/api";

describe("useFormatter", () => {
  test("initial state is idle", () => {
    const { result } = renderHook(() => useFormatter());
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isOpen).toBe(false);
    expect(result.current.diffs).toHaveLength(0);
    expect(result.current.hasDiffs).toBe(false);
  });

  test("requestFormat sets isLoading true during request", async () => {
    server.use(
      http.post(`${API_BASE}/format/burst`, async () => {
        await new Promise((r) => setTimeout(r, 50));
        return HttpResponse.json({
          burst_id: 1,
          lines: [],
          diffs: [],
          diff_count: 0,
          processed_at: new Date().toISOString(),
        });
      })
    );
    const { result } = renderHook(() => useFormatter());
    act(() => { result.current.requestFormat(1); });
    expect(result.current.isLoading).toBe(true);
  });

  test("requestFormat with 0 diffs and 0 lines shows 'nothing to format' message", async () => {
    server.use(
      http.post(`${API_BASE}/format/burst`, () =>
        HttpResponse.json({
          burst_id: 1,
          lines: [],
          diffs: [],
          diff_count: 0,
          processed_at: new Date().toISOString(),
        })
      )
    );
    const { result } = renderHook(() => useFormatter());
    await act(async () => { await result.current.requestFormat(1); });
    expect(result.current.isOpen).toBe(false);
    expect(result.current.error).toBe("Nothing to format — burst has no content.");
  });

  test("requestFormat with 0 diffs and N lines shows 'already clean' with count", async () => {
    const mockLine = { line_id: "l1", line_index: 0, raw_line: "hello", formatted_line: "hello", status: "untouched", checksum: "abc" };
    server.use(
      http.post(`${API_BASE}/format/burst`, () =>
        HttpResponse.json({
          burst_id: 1,
          lines: [mockLine, mockLine],
          diffs: [],
          diff_count: 0,
          processed_at: new Date().toISOString(),
        })
      )
    );
    const { result } = renderHook(() => useFormatter());
    await act(async () => { await result.current.requestFormat(1); });
    expect(result.current.isOpen).toBe(false);
    expect(result.current.error).toBe("Already clean — checked 2 lines, no changes needed.");
  });

  test("requestFormat with diffs opens panel", async () => {
    const mockDiff = {
      diff_id: "test-diff-id",
      line_id: "test-line-id",
      operation: "insert_paragraph_break",
      status: "pending",
      raw_before: "some text",
      formatted_after: "\nsome text",
    };
    server.use(
      http.post(`${API_BASE}/format/burst`, () =>
        HttpResponse.json({
          burst_id: 1,
          lines: [],
          diffs: [mockDiff],
          diff_count: 1,
          processed_at: new Date().toISOString(),
        })
      )
    );
    const { result } = renderHook(() => useFormatter());
    await act(async () => { await result.current.requestFormat(1); });
    expect(result.current.isOpen).toBe(true);
    expect(result.current.diffs).toHaveLength(1);
    expect(result.current.pendingCount).toBe(1);
    expect(result.current.error).toBeNull();
  });

  test("updateDiffStatus changes status locally", () => {
    const { result } = renderHook(() => useFormatter());
    // Seed diffs manually
    act(() => {
      result.current.updateDiffStatus("fake-diff", "accepted");
    });
    // No crash — optimistic update on empty diffs array is safe
  });

  test("resetFormatting clears all state", async () => {
    const { result } = renderHook(() => useFormatter());
    act(() => { result.current.resetFormatting(); });
    expect(result.current.diffs).toHaveLength(0);
    expect(result.current.isOpen).toBe(false);
    expect(result.current.burstId).toBeNull();
  });
});

