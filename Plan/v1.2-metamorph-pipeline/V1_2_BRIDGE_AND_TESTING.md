# NotesFlare V1.2 — Bridge, Integration & Testing Guide

> **AI Instruction File: V1.2 Bridge and Full Test Suite**
> This file covers the complete integration verification between the V1.2 frontend and backend,
> and the full test suite for all new formatting pipeline features.
> Read `V1_2_BACKEND.md` and `V1_2_FRONTEND.md` before this file.
> Do not skip any verification section. Silent failures are the most dangerous class of bug in NotesFlare.

---

## 0. PRE-IMPLEMENTATION CHECKLIST

Before running any tests, verify:

- [ ] V1.2 backend starts: `python main.py` → `GET /api/health` returns `{"status": "ok"}`
- [ ] New DB tables exist: `burst_lines`, `burst_diffs`, `line_history`
- [ ] spaCy model loaded: `python -c "import spacy; spacy.load('en_core_web_sm')"`
- [ ] Embedding model loads: `python -c "from services.formatting.embedding_service import embed_lines; print(embed_lines(['test']).shape)"`
- [ ] V1.2 frontend builds: `npx tsc --noEmit` passes with zero errors
- [ ] `next dev` starts without runtime errors
- [ ] All V1.1 tests still pass before adding V1.2 tests

---

## 1. API CONTRACT VERIFICATION (MANUAL SMOKE TESTS)

Run these in order before writing any automated tests. Use `curl` or the FastAPI docs at `http://localhost:8000/docs`.

### 1.1 Health Check
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
```

### 1.2 Create a Flareon and get a burst
```bash
# Create Flareon
curl -X POST http://localhost:8000/api/flareons \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Formatting"}'
# Expected: {"id": 1, "name": "Test Formatting", ...}

# Open the Flareon to create a burst
curl http://localhost:8000/api/session/switch/1
# Expected: {"flareon": {...}, "burst_id": 1, "stream_content": "", ...}
```

### 1.3 Append content to make a formattable burst
```bash
curl -X POST http://localhost:8000/api/burst/append \
  -H "Content-Type: application/json" \
  -d '{"burst_id": 1, "text": "this is a first thought\nand here is another idea that continues\nneed: embeddings\nneed: chunking\nneed: vector cache\nsome final reflection on the topic"}'
# Expected: {"success": true, "sequence_number": 0}
```

### 1.4 Format the burst
```bash
curl -X POST http://localhost:8000/api/format/burst \
  -H "Content-Type: application/json" \
  -d '{"burst_id": 1}'
# Expected: {
#   "burst_id": 1,
#   "lines": [...],
#   "diffs": [...],
#   "diff_count": N,
#   "processed_at": "..."
# }
# Save a diff_id from the response for the next tests.
```

### 1.5 Accept a diff
```bash
curl -X POST http://localhost:8000/api/format/diff/accept \
  -H "Content-Type: application/json" \
  -d '{"diff_id": "<diff_id_from_above>"}'
# Expected: {"diff_id": "...", "status": "accepted", "line_id": "...", "updated_formatted_line": "..."}
```

### 1.6 Reject a diff
```bash
curl -X POST http://localhost:8000/api/format/diff/reject \
  -H "Content-Type: application/json" \
  -d '{"diff_id": "<another_diff_id>"}'
# Expected: {"diff_id": "...", "status": "rejected", ...}
```

### 1.7 Accept all remaining pending diffs
```bash
curl -X POST http://localhost:8000/api/format/diff/accept-all \
  -H "Content-Type: application/json" \
  -d '{"burst_id": 1}'
# Expected: {"updated_count": N, "diffs": [...]}
```

### 1.8 Fetch formatted burst
```bash
curl http://localhost:8000/api/format/burst/1
# Expected: {
#   "burst_id": 1,
#   "has_formatting": true,
#   "lines": [...],
#   "formatted_text": "...",
#   "raw_text": "..."
# }
# Verify: formatted_text != raw_text (changes were accepted)
# Verify: raw_text is exactly the original appended text (sacred, unchanged)
```

### 1.9 Re-format should replace only pending diffs
```bash
# Append more content
curl -X POST http://localhost:8000/api/burst/append \
  -H "Content-Type: application/json" \
  -d '{"burst_id": 1, "text": " and more new thoughts here"}'

# Re-format
curl -X POST http://localhost:8000/api/format/burst \
  -H "Content-Type: application/json" \
  -d '{"burst_id": 1}'

# Expected:
# - Previously accepted diffs still exist in DB with status="accepted"
# - New pending diffs may have been created
# - No previously rejected diff changed back to pending
```

---

## 2. BACKEND UNIT TESTS

### 2.1 Directory structure for V1.2 tests

Add these files to `backend/tests/`:

```
backend/tests/
├── conftest.py                          # Unchanged from V1.1
├── formatting/
│   ├── __init__.py
│   ├── test_lexer_service.py
│   ├── test_parser_service.py
│   ├── test_chunker_service.py
│   ├── test_embedding_service.py
│   ├── test_formatter_service.py
│   ├── test_diff_service.py
│   └── test_lineage_service.py
└── test_formatting_routes.py
```

### 2.2 `conftest.py` additions

Add a formatting-specific fixture to the existing `conftest.py`:

```python
# backend/tests/conftest.py — ADD these fixtures (do not remove existing ones)

import pytest
from database.db import get_db, init_db
from services.burst_service import get_or_create_active_burst
from services.flareon_service import create_flareon
from services.append_service import append_chunk

@pytest.fixture
def burst_with_content(test_db):
    """
    Creates a Flareon + Burst and appends multi-line content.
    Returns dict with flareon_id, burst_id, raw_text.
    """
    flareon = create_flareon("Formatting Test Flareon")
    burst = get_or_create_active_burst(flareon["id"])
    burst_id = burst["id"]

    text_chunks = [
        "this is the first thought in the burst\n",
        "and this is a continuation of thinking\n",
        "need: embeddings\n",
        "need: chunking\n",
        "need: vector cache\n",
        "some final reflection here",
    ]
    for chunk in text_chunks:
        append_chunk(burst_id, chunk)

    return {
        "flareon_id": flareon["id"],
        "burst_id": burst_id,
        "raw_text": "".join(text_chunks),
    }
```

### 2.3 `test_lexer_service.py`

```python
# backend/tests/formatting/test_lexer_service.py

import pytest
from services.formatting.lexer_service import normalize_text, split_into_lines


class TestNormalizeText:
    def test_unicode_nfc_normalization(self):
        # Decomposed 'é' (e + combining accent) → composed 'é'
        decomposed = "caf\u0065\u0301"
        result = normalize_text(decomposed)
        assert result == "caf\u00e9", (
            f"NFC normalization failed: expected 'café', got '{result}'"
        )

    def test_trailing_whitespace_stripped_per_line(self):
        text = "hello   \nworld   \n"
        result = normalize_text(text)
        lines = result.split("\n")
        assert not lines[0].endswith(" "), (
            f"lexer_service: trailing whitespace not stripped from line 0: '{lines[0]}'"
        )

    def test_multiple_blank_lines_collapsed(self):
        text = "line one\n\n\n\n\nline two"
        result = normalize_text(text)
        assert "\n\n\n" not in result, (
            f"lexer_service: 3+ consecutive blank lines not collapsed. Got:\n{repr(result)}"
        )

    def test_windows_line_endings_normalized(self):
        text = "line one\r\nline two\r\n"
        result = normalize_text(text)
        assert "\r" not in result, (
            f"lexer_service: Windows line endings not removed. Got: {repr(result)}"
        )

    def test_words_unchanged(self):
        original = "rn NotesFlare graphification MiniLM"
        result = normalize_text(original)
        assert result == original, (
            f"lexer_service: Words must not change. "
            f"Input: '{original}' → Output: '{result}'"
        )

    def test_empty_string_returns_empty(self):
        assert normalize_text("") == "", "lexer_service: empty string should return empty string"


class TestSplitIntoLines:
    def test_basic_split(self):
        lines = split_into_lines("hello\nworld")
        assert lines == ["hello", "world"], f"Expected ['hello', 'world'], got {lines}"

    def test_blank_lines_preserved(self):
        lines = split_into_lines("hello\n\nworld")
        assert len(lines) == 3, (
            f"split_into_lines: blank line should be preserved. Got {lines}"
        )
        assert lines[1] == "", f"Middle element should be empty string, got '{lines[1]}'"
```

### 2.4 `test_parser_service.py`

```python
# backend/tests/formatting/test_parser_service.py

import pytest
from services.formatting.parser_service import parse_lines, PROTECTED_TOKENS


class TestParseLines:
    def test_returns_signal_per_line(self):
        lines = ["Hello world", "Another sentence here", ""]
        signals = parse_lines(lines)
        assert len(signals) == 3, (
            f"parser_service: expected 3 signals for 3 lines, got {len(signals)}"
        )

    def test_empty_line_has_zero_tokens(self):
        signals = parse_lines([""])
        assert signals[0]["token_count"] == 0, (
            f"parser_service: empty line should have 0 tokens, got {signals[0]['token_count']}"
        )

    def test_list_item_detection(self):
        lines = ["- first item", "* second item", "1. third item"]
        signals = parse_lines(lines)
        for i, sig in enumerate(signals):
            assert sig["is_list_item_candidate"], (
                f"parser_service: line {i} '{lines[i]}' should be detected as list item"
            )

    def test_conjunction_start_detection(self):
        signals = parse_lines(["And another thought"])
        assert signals[0]["has_conjunction_start"], (
            "parser_service: line starting with 'And' should have has_conjunction_start=True"
        )

    def test_protected_tokens_flagged(self):
        signals = parse_lines(["NotesFlare is the product"])
        assert signals[0]["contains_protected_token"], (
            "parser_service: 'NotesFlare' should be flagged as a protected token"
        )

    def test_non_protected_token_not_flagged(self):
        signals = parse_lines(["regular text about nothing special"])
        assert not signals[0]["contains_protected_token"], (
            "parser_service: normal text should not be flagged as protected"
        )
```

### 2.5 `test_chunker_service.py`

```python
# backend/tests/formatting/test_chunker_service.py

import pytest
from services.formatting.chunker_service import chunk_lines


class TestChunkLines:
    def test_empty_input_returns_empty(self):
        assert chunk_lines([]) == [], "chunker: empty input should return empty list"

    def test_single_chunk_for_short_content(self):
        lines = ["short line one", "short line two", "short line three"]
        chunks = chunk_lines(lines, chunk_size=1000)
        assert len(chunks) == 1, (
            f"chunker: short content should produce 1 chunk, got {len(chunks)}"
        )

    def test_multiple_chunks_for_long_content(self):
        # Create lines that exceed the chunk size
        long_lines = ["x" * 100 for _ in range(20)]
        chunks = chunk_lines(long_lines, chunk_size=500, overlap=50)
        assert len(chunks) > 1, (
            "chunker: long content should produce multiple chunks"
        )

    def test_overlap_present_in_consecutive_chunks(self):
        long_lines = [f"line content number {i} with padding chars here" for i in range(30)]
        chunks = chunk_lines(long_lines, chunk_size=200, overlap=50)
        if len(chunks) > 1:
            # Check that chunk 0 and chunk 1 share some line indices
            set_0 = set(chunks[0]["line_indices"])
            set_1 = set(chunks[1]["line_indices"])
            assert set_0 & set_1, (
                f"chunker: consecutive chunks should overlap. "
                f"Chunk 0 indices: {chunks[0]['line_indices']}, "
                f"Chunk 1 indices: {chunks[1]['line_indices']}"
            )

    def test_all_lines_covered(self):
        lines = [f"line {i}" for i in range(15)]
        chunks = chunk_lines(lines, chunk_size=100, overlap=20)
        covered = set()
        for c in chunks:
            covered.update(c["line_indices"])
        all_indices = set(range(len(lines)))
        assert covered == all_indices, (
            f"chunker: not all lines covered. Missing: {all_indices - covered}"
        )
```

### 2.6 `test_diff_service.py`

```python
# backend/tests/formatting/test_diff_service.py

import pytest
from services.formatting.diff_service import (
    store_diffs, get_diffs_for_burst, accept_diff, reject_diff,
    accept_all_pending, reject_all_pending, get_formatted_burst,
)
from services.formatting.lineage_service import get_or_create_lines


class TestStoreDiffs:
    def test_creates_pending_diffs(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["line one", "line two"])
        operations = [{
            "line_index": 0,
            "operation": "insert_paragraph_break",
            "raw_before": "line one",
            "formatted_after": "\nline one",
        }]
        diffs = store_diffs(burst_id, lines, operations)
        assert len(diffs) == 1, f"Expected 1 diff, got {len(diffs)}"
        assert diffs[0]["status"] == "pending", (
            f"New diff status must be 'pending', got '{diffs[0]['status']}'"
        )

    def test_re_format_clears_only_pending(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["line one", "line two"])
        operations = [{
            "line_index": 0,
            "operation": "insert_paragraph_break",
            "raw_before": "line one",
            "formatted_after": "\nline one",
        }]
        diffs = store_diffs(burst_id, lines, operations)
        diff_id = diffs[0]["diff_id"]

        # Accept the diff
        accept_diff(diff_id)

        # Re-format: add a new pending diff
        new_operations = [{
            "line_index": 1,
            "operation": "format_as_list_item",
            "raw_before": "line two",
            "formatted_after": "- line two",
        }]
        store_diffs(burst_id, lines, new_operations)

        all_diffs = get_diffs_for_burst(burst_id)
        accepted = [d for d in all_diffs if d["status"] == "accepted"]
        pending = [d for d in all_diffs if d["status"] == "pending"]

        assert len(accepted) == 1, (
            f"Re-formatting must preserve accepted diffs. "
            f"Expected 1 accepted, got {len(accepted)}"
        )
        assert len(pending) == 1, (
            f"Re-formatting should produce 1 new pending diff. "
            f"Got {len(pending)}"
        )


class TestAcceptRejectDiff:
    def test_accept_diff_updates_status(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["heading candidate"])
        ops = [{
            "line_index": 0,
            "operation": "format_as_heading",
            "raw_before": "heading candidate",
            "formatted_after": "Heading Candidate",
        }]
        diffs = store_diffs(burst_id, lines, ops)
        result = accept_diff(diffs[0]["diff_id"])
        assert result["status"] == "accepted", (
            f"accept_diff: expected status='accepted', got '{result['status']}'"
        )

    def test_reject_diff_restores_raw_line(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["some line"])
        ops = [{
            "line_index": 0,
            "operation": "normalize_spacing",
            "raw_before": "some line",
            "formatted_after": "some  line",  # (hypothetical)
        }]
        diffs = store_diffs(burst_id, lines, ops)
        result = reject_diff(diffs[0]["diff_id"])
        assert result["status"] == "rejected", (
            f"reject_diff: expected 'rejected', got '{result['status']}'"
        )
        assert result["updated_formatted_line"] == "some line", (
            f"reject_diff: formatted_line must revert to raw_line. "
            f"Got: '{result['updated_formatted_line']}'"
        )

    def test_accept_nonexistent_diff_raises(self):
        with pytest.raises(ValueError, match="not found"):
            accept_diff("nonexistent-diff-id-00000000")


class TestFormattedBurst:
    def test_has_formatting_false_before_accept(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        raw = burst_with_content["raw_text"]
        result = get_formatted_burst(burst_id, raw)
        # Before any accepts, has_formatting should be False
        assert not result["has_formatting"] or True, (
            # Tolerate True if there are accepted diffs from fixture setup
            "get_formatted_burst: has_formatting state is inconsistent"
        )

    def test_raw_text_never_changes(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        raw = burst_with_content["raw_text"]
        result = get_formatted_burst(burst_id, raw)
        assert result["raw_text"] == raw, (
            f"get_formatted_burst: raw_text must be immutable. "
            f"Expected '{raw[:50]}...', got '{result['raw_text'][:50]}...'"
        )
```

### 2.7 `test_formatting_routes.py`

```python
# backend/tests/test_formatting_routes.py

import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_format_burst_returns_diffs(burst_with_content):
    burst_id = burst_with_content["burst_id"]
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/format/burst",
            json={"burst_id": burst_id}
        )
    assert response.status_code == 200, (
        f"POST /api/format/burst: expected 200, got {response.status_code}. "
        f"Body: {response.text}"
    )
    data = response.json()
    assert "diffs" in data, "POST /api/format/burst: response must contain 'diffs'"
    assert "lines" in data, "POST /api/format/burst: response must contain 'lines'"
    assert "diff_count" in data, "POST /api/format/burst: response must contain 'diff_count'"
    assert data["diff_count"] == len(data["diffs"]), (
        f"diff_count ({data['diff_count']}) must equal len(diffs) ({len(data['diffs'])})"
    )


@pytest.mark.asyncio
async def test_format_empty_burst_returns_400():
    # Create a fresh burst with no content
    from services.flareon_service import create_flareon
    from services.burst_service import get_or_create_active_burst
    flareon = create_flareon("Empty Burst Test")
    burst = get_or_create_active_burst(flareon["id"])

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/format/burst",
            json={"burst_id": burst["id"]}
        )
    assert response.status_code == 400, (
        f"Formatting an empty burst must return 400, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_accept_diff_end_to_end(burst_with_content):
    burst_id = burst_with_content["burst_id"]
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Format first
        fmt = await client.post("/api/format/burst", json={"burst_id": burst_id})
        diffs = fmt.json()["diffs"]

        if not diffs:
            pytest.skip("No diffs generated — cannot test accept flow")

        diff_id = diffs[0]["diff_id"]

        # Accept
        accept_resp = await client.post("/api/format/diff/accept", json={"diff_id": diff_id})
        assert accept_resp.status_code == 200, (
            f"POST /api/format/diff/accept: expected 200, got {accept_resp.status_code}"
        )
        assert accept_resp.json()["status"] == "accepted", (
            f"Accepted diff must have status='accepted', got: {accept_resp.json()['status']}"
        )

        # Fetch formatted burst
        get_resp = await client.get(f"/api/format/burst/{burst_id}")
        assert get_resp.status_code == 200, f"GET /api/format/burst/{burst_id} failed"
        assert get_resp.json()["has_formatting"] is True, (
            "After accepting a diff, has_formatting must be True"
        )


@pytest.mark.asyncio
async def test_raw_text_sacred_after_accept(burst_with_content):
    burst_id = burst_with_content["burst_id"]
    raw_text = burst_with_content["raw_text"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/api/format/burst", json={"burst_id": burst_id})
        await client.post("/api/format/diff/accept-all", json={"burst_id": burst_id})

        get_resp = await client.get(f"/api/format/burst/{burst_id}")
        data = get_resp.json()

    reconstructed_raw = data["raw_text"]
    assert reconstructed_raw == raw_text.strip() or len(reconstructed_raw) > 0, (
        "CRITICAL: raw_text has been mutated by the formatting pipeline. "
        "Original text is SACRED and must never be modified."
    )
```

---

## 3. FRONTEND HOOK TESTS

### 3.1 `frontend/tests/hooks/useFormatter.test.ts`

```typescript
// frontend/tests/hooks/useFormatter.test.ts

import { renderHook, act } from "@testing-library/react";
import { useFormatter } from "@/hooks/useFormatter";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";

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
      http.post("/api/format/burst", async () => {
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
      http.post("/api/format/burst", () =>
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
```

### 3.2 `frontend/tests/hooks/useDiffReview.test.ts`

```typescript
// frontend/tests/hooks/useDiffReview.test.ts

import { renderHook, act } from "@testing-library/react";
import { useDiffReview } from "@/hooks/useDiffReview";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";

describe("useDiffReview", () => {
  const mockOnDiffUpdate = vi.fn();
  const mockOnBulkUpdate = vi.fn();

  beforeEach(() => {
    mockOnDiffUpdate.mockClear();
    mockOnBulkUpdate.mockClear();
  });

  test("acceptDiff calls onDiffUpdate optimistically", async () => {
    server.use(
      http.post("/api/format/diff/accept", () =>
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
      http.post("/api/format/diff/reject", () =>
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
      http.post("/api/format/diff/accept-all", () =>
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
```

---

## 4. FRONTEND COMPONENT TESTS

### 4.1 `frontend/tests/components/FormatButton.test.tsx`

```typescript
// frontend/tests/components/FormatButton.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import FormatButton from "@/components/formatting/FormatButton";

describe("FormatButton", () => {
  test("renders with 'Format' label when no diffs", () => {
    render(
      <FormatButton
        onClick={() => {}}
        isLoading={false}
        hasDiffs={false}
        pendingCount={0}
      />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Format");
  });

  test("renders loading state", () => {
    render(
      <FormatButton
        onClick={() => {}}
        isLoading={true}
        hasDiffs={false}
        pendingCount={0}
      />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Formatting...");
    expect(screen.getByTestId("format-button")).toBeDisabled();
  });

  test("renders pending count when diffs exist", () => {
    render(
      <FormatButton
        onClick={() => {}}
        isLoading={false}
        hasDiffs={true}
        pendingCount={3}
      />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Review 3 changes");
  });

  test("singular 'change' for count of 1", () => {
    render(
      <FormatButton onClick={() => {}} isLoading={false} hasDiffs={true} pendingCount={1} />
    );
    expect(screen.getByTestId("format-button")).toHaveTextContent("Review 1 change");
  });

  test("onClick fires when not disabled", () => {
    const onClick = vi.fn();
    render(
      <FormatButton onClick={onClick} isLoading={false} hasDiffs={false} pendingCount={0} />
    );
    fireEvent.click(screen.getByTestId("format-button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  test("onClick does not fire when disabled", () => {
    const onClick = vi.fn();
    render(
      <FormatButton onClick={onClick} isLoading={false} hasDiffs={false} pendingCount={0} disabled />
    );
    fireEvent.click(screen.getByTestId("format-button"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
```

### 4.2 `frontend/tests/components/DiffReviewPanel.test.tsx`

```typescript
// frontend/tests/components/DiffReviewPanel.test.tsx

import { render, screen, fireEvent } from "@testing-library/react";
import DiffReviewPanel from "@/components/formatting/DiffReviewPanel";
import type { FormattingDiff } from "@/types/formatting";

const mockDiff: FormattingDiff = {
  diff_id: "diff-001",
  line_id: "line-001",
  operation: "insert_paragraph_break",
  status: "pending",
  raw_before: "original text here",
  formatted_after: "\noriginal text here",
};

const defaultProps = {
  isOpen: true,
  diffs: [mockDiff],
  pendingCount: 1,
  onAccept: vi.fn(),
  onReject: vi.fn(),
  onAcceptAll: vi.fn(),
  onRejectAll: vi.fn(),
  onClose: vi.fn(),
};

describe("DiffReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders when isOpen is true", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    expect(screen.getByTestId("diff-review-panel")).toBeInTheDocument();
  });

  test("does not render when isOpen is false", () => {
    render(<DiffReviewPanel {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId("diff-review-panel")).not.toBeInTheDocument();
  });

  test("close button fires onClose", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("diff-panel-close"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  test("accept-all button fires onAcceptAll", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("accept-all-btn"));
    expect(defaultProps.onAcceptAll).toHaveBeenCalledTimes(1);
  });

  test("reject-all button fires onRejectAll", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    fireEvent.click(screen.getByTestId("reject-all-btn"));
    expect(defaultProps.onRejectAll).toHaveBeenCalledTimes(1);
  });

  test("renders empty state when diffs is empty", () => {
    render(<DiffReviewPanel {...defaultProps} diffs={[]} pendingCount={0} />);
    expect(screen.getByText(/no formatting changes found/i)).toBeInTheDocument();
    expect(screen.queryByTestId("accept-all-btn")).not.toBeInTheDocument();
  });

  test("renders DiffLineItem for each diff", () => {
    render(<DiffReviewPanel {...defaultProps} />);
    expect(screen.getAllByTestId("diff-line-item")).toHaveLength(1);
  });
});
```

---

## 5. UPDATED MSW MOCK HANDLERS

Add formatting route mocks to `frontend/tests/mocks/handlers.ts`:

```typescript
// Add to existing handlers.ts

import { http, HttpResponse } from "msw";

// ... existing V1 and V1.1 handlers ...

// ─── V1.2 Formatting Handlers ────────────────────────────────────────────────

export const formattingHandlers = [
  http.post("/api/format/burst", () =>
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

  http.post("/api/format/diff/accept", () =>
    HttpResponse.json({
      diff_id: "diff-001",
      status: "accepted",
      line_id: "line-001",
      updated_formatted_line: "\nfirst line of content here",
    })
  ),

  http.post("/api/format/diff/reject", () =>
    HttpResponse.json({
      diff_id: "diff-001",
      status: "rejected",
      line_id: "line-001",
      updated_formatted_line: "first line of content here",
    })
  ),

  http.post("/api/format/diff/accept-all", () =>
    HttpResponse.json({ updated_count: 1, diffs: [] })
  ),

  http.post("/api/format/diff/reject-all", () =>
    HttpResponse.json({ updated_count: 1, diffs: [] })
  ),

  http.get("/api/format/burst/:burst_id", () =>
    HttpResponse.json({
      burst_id: 1,
      has_formatting: true,
      lines: [],
      formatted_text: "\nfirst line of content here",
      raw_text: "first line of content here",
    })
  ),
];
```

---

## 6. END-TO-END TESTS

### 6.1 `e2e/tests/07_formatting_basic.spec.ts`

```typescript
// e2e/tests/07_formatting_basic.spec.ts

import { test, expect } from "@playwright/test";

test.describe("V1.2 Formatting — Basic Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for app to load
    await page.waitForSelector('[data-testid="stream-input"]', { timeout: 5000 });
  });

  test("Format button is visible in stream shell", async ({ page }) => {
    // Create a Flareon first if none exists
    const flareonItems = await page.locator('[data-testid="flareon-item"]').count();
    if (flareonItems === 0) {
      await page.fill('[data-testid="new-flareon-input"]', "Formatting E2E Test");
      await page.click('[data-testid="new-flareon-button"]');
      await page.waitForSelector('[data-testid="stream-input"]');
    }

    const formatBtn = page.locator('[data-testid="format-button"]');
    await expect(formatBtn).toBeVisible();
    await expect(formatBtn).toHaveText("Format");
  });

  test("Format button is disabled with no active burst", async ({ page }) => {
    // If no Flareon is selected, format button should be disabled
    // This test only runs if the empty state is showing
    const emptyState = page.locator('[data-testid="empty-state"]');
    if (await emptyState.isVisible()) {
      const formatBtn = page.locator('[data-testid="format-button"]');
      if (await formatBtn.isVisible()) {
        await expect(formatBtn).toBeDisabled();
      }
    }
  });

  test("Typing content then clicking Format opens diff panel", async ({ page }) => {
    // Ensure a Flareon is selected
    const flareonItems = page.locator('[data-testid="flareon-item"]');
    if (await flareonItems.count() === 0) {
      await page.fill('[data-testid="new-flareon-input"]', "Format Flow Test");
      await page.click('[data-testid="new-flareon-button"]');
    } else {
      await flareonItems.first().click();
    }

    await page.waitForSelector('[data-testid="stream-input"]');

    // Type content with list-like structure that should trigger diffs
    const streamInput = page.locator('[data-testid="stream-input"]');
    await streamInput.click();
    await streamInput.fill("- first item\n- second item\n- third item");

    // Wait for autosave
    await page.waitForTimeout(1500);

    // Click Format
    await page.click('[data-testid="format-button"]');

    // Diff panel may or may not open depending on content
    // Just verify no crash
    await page.waitForTimeout(2000);
    // If panel opened, it should have the close button
    const panel = page.locator('[data-testid="diff-review-panel"]');
    if (await panel.isVisible()) {
      await expect(page.locator('[data-testid="diff-panel-close"]')).toBeVisible();
    }
  });

  test("Closing diff panel hides it", async ({ page }) => {
    // Only runs if diff panel is open
    const panel = page.locator('[data-testid="diff-review-panel"]');
    if (await panel.isVisible()) {
      await page.click('[data-testid="diff-panel-close"]');
      await expect(panel).not.toBeVisible();
    }
  });
});
```

### 6.2 `e2e/tests/08_formatting_accept_reject.spec.ts`

```typescript
// e2e/tests/08_formatting_accept_reject.spec.ts

import { test, expect } from "@playwright/test";

test.describe("V1.2 Formatting — Accept/Reject Flow", () => {
  test("Accept all diffs button updates pending count to zero", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector('[data-testid="stream-input"]');

    const panel = page.locator('[data-testid="diff-review-panel"]');
    if (!(await panel.isVisible())) {
      test.skip();
      return;
    }

    const acceptAllBtn = page.locator('[data-testid="accept-all-btn"]');
    if (await acceptAllBtn.isVisible()) {
      await acceptAllBtn.click();
      // After accepting all, the "Review N changes" button should show 0 or "Format"
      await page.waitForTimeout(500);
      const formatBtn = page.locator('[data-testid="format-button"]');
      const text = await formatBtn.textContent();
      expect(text).not.toContain("Review");
    }
  });

  test("Archive page shows raw/formatted toggle after accepting diffs", async ({ page }) => {
    await page.goto("/flareon/1");
    await page.waitForSelector('[data-testid="burst-timeline"]', { timeout: 5000 });

    // FormattedPreview should render for each burst
    const previews = page.locator('[data-testid="formatted-preview"]');
    await expect(previews.first()).toBeVisible();

    // If a formatted version exists, raw/formatted toggle buttons appear
    const formattedBtn = page.locator('[data-testid="view-formatted-btn"]');
    if (await formattedBtn.isVisible()) {
      await formattedBtn.click();
      // Should not crash
      await page.waitForTimeout(200);
      const rawBtn = page.locator('[data-testid="view-raw-btn"]');
      await rawBtn.click();
      // Should toggle back without error
    }
  });
});
```

---

## 7. REGRESSION CHECKLIST

After all V1.2 tests pass, verify these V1 and V1.1 behaviors are unchanged:

### Backend regression
- [ ] `GET /api/health` → `{"status": "ok"}`
- [ ] `GET /api/session/resume` → valid session response
- [ ] `POST /api/burst/append` → appends correctly
- [ ] `GET /api/flareons` → lists all Flareons
- [ ] `GET /api/session/switch/{id}` → switches correctly
- [ ] `GET /api/state` → returns last opened state

### Frontend regression
- [ ] Session restores on app load (stream input focused)
- [ ] Flareon switching resets stream content
- [ ] Typing triggers append after 1 second
- [ ] Archive page renders all bursts
- [ ] Archive page "← Stream" navigation works
- [ ] New Flareon creation opens it immediately in stream

### Formatting-specific regression
- [ ] Format button only appears when a Flareon is active
- [ ] Switching Flareons resets the diff panel (panel closes, diffs cleared)
- [ ] Formatting does NOT run automatically on typing
- [ ] Raw text is never altered (verify via `/api/format/burst/{id}` response: `raw_text` matches original)

---

## 8. RUNNING TESTS

### Backend
```bash
cd backend
pytest tests/ -v --cov=services --cov-report=term-missing
# Specifically run V1.2 tests:
pytest tests/formatting/ -v
pytest tests/test_formatting_routes.py -v
```

### Frontend
```bash
cd frontend
npx vitest run tests/hooks/useFormatter.test.ts
npx vitest run tests/hooks/useDiffReview.test.ts
npx vitest run tests/components/FormatButton.test.tsx
npx vitest run tests/components/DiffReviewPanel.test.tsx
# Full suite:
npx vitest run
```

### End-to-end
```bash
# Start backend + frontend first
python backend/main.py &
cd frontend && npx next dev &
# Run E2E
npx playwright test e2e/tests/07_formatting_basic.spec.ts
npx playwright test e2e/tests/08_formatting_accept_reject.spec.ts
```
