// frontend/tests/hooks/useDiffReview.test.ts

import { renderHook, act } from "@testing-library/react";
import { useDiffReview } from "@/hooks/useDiffReview";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";

const API_BASE = "http://127.0.0.1:8000/api";

describe("useDiffReview", () => {
  const mockOnDiffUpdate = vi.fn();
  const mockOnBulkUpdate = vi.fn();

  beforeEach(() => {
    mockOnDiffUpdate.mockClear();
    mockOnBulkUpdate.mockClear();
  });

  test("acceptDiff calls onDiffUpdate optimistically", async () => {
    server.use(
      http.post(`${API_BASE}/format/diff/accept`, () =>
        HttpResponse.json({
          diff_id: "d1",
          status: "accepted",
          line_id: "l1",
          updated_formatted_line: "Formatted Line",
        })
      )
    );
    const { result } = renderHook(() =>
      useDiffReview({
        burstId: 1,
        onDiffUpdate: mockOnDiffUpdate,
        onBulkUpdate: mockOnBulkUpdate,
      })
    );
    await act(async () => { await result.current.acceptDiff("d1"); });
    expect(mockOnDiffUpdate).toHaveBeenCalledWith("d1", "accepted");
  });

  test("rejectDiff calls onDiffUpdate optimistically", async () => {
    server.use(
      http.post(`${API_BASE}/format/diff/reject`, () =>
        HttpResponse.json({
          diff_id: "d2",
          status: "rejected",
          line_id: "l2",
          updated_formatted_line: "original line",
        })
      )
    );
    const { result } = renderHook(() =>
      useDiffReview({
        burstId: 1,
        onDiffUpdate: mockOnDiffUpdate,
        onBulkUpdate: mockOnBulkUpdate,
      })
    );
    await act(async () => { await result.current.rejectDiff("d2"); });
    expect(mockOnDiffUpdate).toHaveBeenCalledWith("d2", "rejected");
  });

  test("acceptAll calls onBulkUpdate with 'accepted'", async () => {
    server.use(
      http.post(`${API_BASE}/format/diff/accept-all`, () =>
        HttpResponse.json({ updated_count: 3, diffs: [] })
      )
    );
    const { result } = renderHook(() =>
      useDiffReview({
        burstId: 1,
        onDiffUpdate: mockOnDiffUpdate,
        onBulkUpdate: mockOnBulkUpdate,
      })
    );
    await act(async () => { await result.current.acceptAll(); });
    expect(mockOnBulkUpdate).toHaveBeenCalledWith("accepted");
  });

  test("acceptAll is no-op when burstId is null", async () => {
    const { result } = renderHook(() =>
      useDiffReview({
        burstId: null,
        onDiffUpdate: mockOnDiffUpdate,
        onBulkUpdate: mockOnBulkUpdate,
      })
    );
    await act(async () => { await result.current.acceptAll(); });
    expect(mockOnBulkUpdate).not.toHaveBeenCalled();
  });
});
