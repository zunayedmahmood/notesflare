// frontend/tests/hooks/useAutosave.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutosave } from '@/hooks/useAutosave';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    appendChunk: vi.fn(),
  },
}));

describe('useAutosave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(api.appendChunk).mockClear();
    vi.mocked(api.appendChunk).mockResolvedValue({ success: true, sequence_number: 0 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not save if burstId is null', async () => {
    const getDelta = vi.fn().mockReturnValue('some content');
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useAutosave({ burstId: null, getDelta, onSaveSuccess })
    );

    act(() => {
      result.current.scheduleAppend();
    });

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(api.appendChunk).not.toHaveBeenCalled();
  });

  it('does not save if getDelta returns empty string', async () => {
    const getDelta = vi.fn().mockReturnValue('');
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useAutosave({ burstId: 1, getDelta, onSaveSuccess })
    );

    act(() => {
      result.current.scheduleAppend();
    });

    await act(async () => {
      vi.advanceTimersByTime(2000);
    });

    expect(api.appendChunk).not.toHaveBeenCalled();
  });

  it('saves after 1000ms of inactivity', async () => {
    const getDelta = vi.fn().mockReturnValue('Hello');
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useAutosave({ burstId: 1, getDelta, onSaveSuccess })
    );

    act(() => {
      result.current.scheduleAppend();
    });

    await act(async () => {
      vi.advanceTimersByTime(1000);
    });

    expect(api.appendChunk).toHaveBeenCalledTimes(1);
    expect(api.appendChunk).toHaveBeenCalledWith(1, 'Hello');
    expect(onSaveSuccess).toHaveBeenCalledTimes(1);
  });

  it('does NOT save before 1000ms', async () => {
    const getDelta = vi.fn().mockReturnValue('Typing...');
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useAutosave({ burstId: 1, getDelta, onSaveSuccess })
    );

    act(() => {
      result.current.scheduleAppend();
    });

    await act(async () => {
      vi.advanceTimersByTime(999);
    });

    expect(api.appendChunk).not.toHaveBeenCalled();
  });

  it('resets timer when scheduleAppend is called rapidly', async () => {
    const getDelta = vi.fn().mockReturnValue('ABC');
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useAutosave({ burstId: 1, getDelta, onSaveSuccess })
    );

    act(() => {
      result.current.scheduleAppend();
    });
    await act(async () => { vi.advanceTimersByTime(500); });

    act(() => {
      result.current.scheduleAppend();
    });
    await act(async () => { vi.advanceTimersByTime(500); });

    act(() => {
      result.current.scheduleAppend();
    });
    await act(async () => { vi.advanceTimersByTime(500); });

    // Only 500ms since last trigger — should not have fired yet
    expect(api.appendChunk).not.toHaveBeenCalled();

    // Now let the remaining 500ms pass after last change (total 1000ms since last trigger)
    await act(async () => { vi.advanceTimersByTime(500); });

    expect(api.appendChunk).toHaveBeenCalledTimes(1);
    expect(api.appendChunk).toHaveBeenCalledWith(1, 'ABC');
    expect(onSaveSuccess).toHaveBeenCalledTimes(1);
  });
});
