// frontend/tests/hooks/useAutosave.test.ts
/**
 * Tests: useAutosave hook
 *
 * Critical behaviors:
 * - Save must fire AFTER 1000ms of inactivity (not before)
 * - Rapid typing resets the timer (debounce)
 * - No save fires when burstId is null
 * - Save is silent — no state change visible to caller
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutosave } from '@/hooks/useAutosave';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    saveContent: vi.fn(),
  },
}));

describe('useAutosave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(api.saveContent).mockClear();
    vi.mocked(api.saveContent).mockResolvedValue({ success: true, burst_entry_id: 1 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not save if burstId is null', async () => {
    const { rerender } = renderHook(
      ({ burstId, content }) => useAutosave(burstId, content),
      { initialProps: { burstId: null as number | null, content: 'initial' } }
    );
    
    // Attempt to change content while burstId is null
    rerender({ burstId: null, content: 'some content' });
    await act(async () => { vi.advanceTimersByTime(2000); });

    expect(api.saveContent).not.toHaveBeenCalled();
  }, {
    onFail: () => `[useAutosave] Save was called with null burstId.
  Expected : api.saveContent NOT called
  Got      : api.saveContent called ${vi.mocked(api.saveContent).mock.calls.length} time(s)
  Fix      : useAutosave must guard: if (!burstId) return; before setting the timer.
  Consequence: POST /api/save would fire with burst_id: null, causing a 500 from the backend.`
  });

  it('does not save immediately on mount', async () => {
    renderHook(() => useAutosave(1, 'initial content'));
    // Do NOT advance timers

    expect(api.saveContent).not.toHaveBeenCalled();
  });

  it('saves after 1000ms of no content change', async () => {
    const { rerender } = renderHook(
      ({ content }) => useAutosave(1, content),
      { initialProps: { content: 'initial' } }
    );

    // Simulate user typing
    rerender({ content: 'Hello world' });

    await act(async () => { vi.advanceTimersByTime(1000); });

    expect(api.saveContent).toHaveBeenCalledTimes(1);
    expect(api.saveContent).toHaveBeenCalledWith(1, 'Hello world');
  });

  it('does NOT save before 1000ms', async () => {
    const { rerender } = renderHook(
      ({ content }) => useAutosave(1, content),
      { initialProps: { content: 'initial' } }
    );

    // Simulate user typing
    rerender({ content: 'Typing...' });

    await act(async () => { vi.advanceTimersByTime(999); });

    expect(api.saveContent).not.toHaveBeenCalled();
  }, {
    onFail: () => `[useAutosave] Save fired before the 1000ms debounce delay.
  Elapsed  : 999ms
  Expected : 0 save calls
  Got      : ${vi.mocked(api.saveContent).mock.calls.length} save call(s)
  Fix      : SAVE_DELAY_MS must be 1000. Check the setTimeout value in useAutosave.ts.`
  });

  it('resets timer when content changes rapidly', async () => {
    const { rerender } = renderHook(
      ({ content }) => useAutosave(1, content),
      { initialProps: { content: 'initial' } }
    );

    // Typing sequence with 500ms intervals
    rerender({ content: 'A' });
    await act(async () => { vi.advanceTimersByTime(500); });
    
    rerender({ content: 'AB' });
    await act(async () => { vi.advanceTimersByTime(500); });
    
    rerender({ content: 'ABC' });
    await act(async () => { vi.advanceTimersByTime(500); });

    // Only 500ms since last change — should not have fired yet
    expect(api.saveContent).not.toHaveBeenCalled();

    // Now let the full 1000ms pass after last change
    await act(async () => { vi.advanceTimersByTime(500); });

    expect(api.saveContent).toHaveBeenCalledTimes(1);
    expect(api.saveContent).toHaveBeenCalledWith(1, 'ABC');
  }, {
    onFail: () => `[useAutosave] Debounce is not resetting on content change.
  Scenario : content changed at t=0, t=500, t=1000 (500ms intervals)
  Expected : Exactly 1 save call, at t=2000ms (1000ms after last change)
  Got      : ${vi.mocked(api.saveContent).mock.calls.length} save call(s)
  Fix      : useEffect must clearTimeout(timer) before setting a new one.
             Pattern: const timer = setTimeout(...); return () => clearTimeout(timer);`
  });
});
