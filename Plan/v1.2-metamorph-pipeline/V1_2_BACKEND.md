# NotesFlare V1.2 — Backend Implementation Guide

> **AI Instruction File: V1.2 Backend Changes**
> This file drives all Python/FastAPI/SQLite changes required for V1.2 — the Formatting Pipeline.
> Read `01_BRAND_AND_ARCHITECTURE.md`, `02_BACKEND.md`, and `V1_1_BACKEND.md` before this file.
> Every decision here supersedes corresponding sections in earlier backend files where they conflict.
> Do not implement anything not described here. Do not skip verification steps.

---

## 0. PRE-IMPLEMENTATION CHECKLIST

Before writing a single line of code, verify:

- [ ] You have read `01_BRAND_AND_ARCHITECTURE.md` in full
- [ ] You have read `02_BACKEND.md` in full
- [ ] You have read `V1_1_BACKEND.md` in full
- [ ] The V1.1 backend starts with `python main.py` and `GET /api/health` returns `{"status": "ok"}`
- [ ] `GET /api/session/resume` returns a valid response
- [ ] `POST /api/burst/append` returns a valid response

If any of the above is false, do NOT proceed. Fix the baseline first.

**Scope of changes in this file:**

1. New Python dependencies: `spacy`, `onnxruntime`, `sentence-transformers`
2. Database schema additions — 3 new tables: `burst_lines`, `burst_diffs`, `line_history`
3. New service: `formatting/lexer_service.py` — whitespace/unicode normalization
4. New service: `formatting/parser_service.py` — spaCy NLP structural parsing
5. New service: `formatting/chunker_service.py` — overlapping sliding window chunking
6. New service: `formatting/embedding_service.py` — MiniLM via ONNX Runtime
7. New service: `formatting/formatter_service.py` — rule-driven structural formatter
8. New service: `formatting/diff_service.py` — line-level diff generation and storage
9. New service: `formatting/lineage_service.py` — stable line ID management
10. New Pydantic schemas: `models/formatting_schemas.py`
11. New API routes: `api/formatting_routes.py`
12. Registration of new routes in `main.py`
13. Updated `requirements.txt`
14. Verification checklist

---

## 1. WHY THE BACKEND CHANGES

V1.1 stored raw text. The user typed and the backend appended chunks. Nothing processed the content.

V1.2 adds a **processing pipeline** that runs on demand (never automatically). When the user clicks "Format", the backend:

1. Reconstructs the full burst text from `burst_entries`
2. Passes it through lexical preprocessing (whitespace normalization)
3. Parses it with spaCy (sentence boundaries, POS tags, structure detection)
4. Optionally chunks and embeds it with MiniLM for semantic coherence (Phase 7)
5. Applies rule-driven formatting detection (paragraph breaks, lists, headings, quotes)
6. Generates a set of line-level diffs (structural operations)
7. Stores the diffs in the database with `status = "pending"`
8. Returns diffs to the frontend for user review

### Immutable Rule
The original `burst_entries` content is NEVER modified by the formatting pipeline. Formatting only writes to `burst_lines`, `burst_diffs`, and `line_history`. The raw text remains sacred.

### What does NOT change in V1.2 backend
- `flareon_service.py` — no changes
- `burst_service.py` — no changes
- `storage_service.py` — no changes
- `append_service.py` — no changes
- `stream_service.py` — no changes
- `session_service.py` — no changes
- `database/db.py` — migration additions only
- All existing V1 and V1.1 API routes — unchanged, additive only

---

## 2. NEW DIRECTORY STRUCTURE

```
backend/
├── api/
│   ├── routes.py                    # Unchanged from V1.1
│   └── formatting_routes.py         # NEW — all /api/format/* endpoints
│
├── services/
│   ├── flareon_service.py           # Unchanged
│   ├── burst_service.py             # Unchanged
│   ├── storage_service.py           # Unchanged
│   ├── append_service.py            # Unchanged
│   ├── stream_service.py            # Unchanged
│   ├── session_service.py           # Unchanged
│   │
│   └── formatting/                  # NEW directory
│       ├── __init__.py
│       ├── lexer_service.py         # Whitespace/unicode normalization
│       ├── parser_service.py        # spaCy NLP parsing
│       ├── chunker_service.py       # Sliding window chunking
│       ├── embedding_service.py     # MiniLM ONNX embeddings
│       ├── formatter_service.py     # Rule-driven structural formatter
│       ├── diff_service.py          # Diff generation and storage
│       └── lineage_service.py       # Stable line ID management
│
├── database/
│   ├── db.py                        # MODIFIED — new migration
│   └── schema.sql                   # MODIFIED — 3 new tables
│
├── models/
│   ├── schemas.py                   # Unchanged from V1.1
│   └── formatting_schemas.py        # NEW — formatting Pydantic models
│
└── main.py                          # MODIFIED — registers formatting_routes
```

---

## 3. DATABASE SCHEMA ADDITIONS

### 3.1 New tables in `schema.sql`

**Append** these table definitions to the existing `schema.sql`. Do NOT modify any existing table definitions.

```sql
-- ─── V1.2: Burst Lines ───────────────────────────────────────────────────────
-- Stable line identity for a burst. One row per line, assigned when formatting
-- first runs on a burst. Lines are immutable once created.

CREATE TABLE IF NOT EXISTS burst_lines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id         TEXT    NOT NULL UNIQUE,   -- Stable UUID assigned at creation
    burst_id        INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    line_index      INTEGER NOT NULL,          -- 0-based position in burst
    raw_line        TEXT    NOT NULL DEFAULT '',
    formatted_line  TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'untouched'
                    CHECK (status IN ('untouched', 'pending', 'accepted', 'rejected')),
    checksum        TEXT    NOT NULL DEFAULT '',  -- SHA256 of raw_line
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_burst_lines_burst_id
    ON burst_lines(burst_id, line_index);

-- ─── V1.2: Burst Diffs ───────────────────────────────────────────────────────
-- One diff per structural change proposed by the formatter.
-- diff_id is a stable UUID. status tracks user review decision.

CREATE TABLE IF NOT EXISTS burst_diffs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    diff_id         TEXT    NOT NULL UNIQUE,   -- Stable UUID
    burst_id        INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    line_id         TEXT    NOT NULL REFERENCES burst_lines(line_id) ON DELETE CASCADE,
    operation       TEXT    NOT NULL,          -- See DiffOperationType enum
    status          TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'accepted', 'rejected')),
    raw_before      TEXT    NOT NULL DEFAULT '',
    formatted_after TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_burst_diffs_burst_id
    ON burst_diffs(burst_id, status);

-- ─── V1.2: Line History ──────────────────────────────────────────────────────
-- Immutable audit trail for every operation on a burst line.
-- Never updated — only inserted.

CREATE TABLE IF NOT EXISTS line_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id      TEXT    NOT NULL UNIQUE,
    line_id         TEXT    NOT NULL,          -- References burst_lines.line_id
    operation       TEXT    NOT NULL,          -- 'create', 'split', 'accept', 'reject', 'reset'
    detail          TEXT,                      -- JSON blob with operation context
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### 3.2 Migration function in `db.py`

Add a `migrate_to_v1_2` function to `database/db.py`. Append it after `migrate_to_v1_1`:

```python
def migrate_to_v1_2(db: sqlite3.Connection) -> None:
    """
    V1.2 migration: add burst_lines, burst_diffs, line_history tables.
    Guard: only runs if burst_lines does not already exist.
    Safe to run on a fresh database (schema.sql already creates them).
    """
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='burst_lines'"
    ).fetchall()

    if not rows:
        print("[migrate] V1.2: Creating formatting tables (burst_lines, burst_diffs, line_history)...")
        # Tables are created by schema.sql on next executescript call.
        # This guard just prevents double-logging.
        print("[migrate] V1.2: Complete.")
```

Update `init_db()` to call it:

```python
def init_db() -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    db = get_db()
    db.executescript(schema_sql)
    migrate_to_v1_1(db)    # Existing V1.1 migration
    migrate_to_v1_2(db)    # New V1.2 migration
    db.commit()
```

---

## 4. NEW PYDANTIC SCHEMAS: `models/formatting_schemas.py`

Create this file. Do not add these to the existing `schemas.py`.

```python
# models/formatting_schemas.py

from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class LineStatus(str, Enum):
    untouched = "untouched"
    pending   = "pending"
    accepted  = "accepted"
    rejected  = "rejected"


class DiffOperationType(str, Enum):
    insert_paragraph_break = "insert_paragraph_break"
    insert_line_break      = "insert_line_break"
    format_as_list_item    = "format_as_list_item"
    format_as_heading      = "format_as_heading"
    format_as_quote        = "format_as_quote"
    normalize_spacing      = "normalize_spacing"


# ─── Line ─────────────────────────────────────────────────────────────────────

class BurstLineResponse(BaseModel):
    line_id:        str
    line_index:     int
    raw_line:       str
    formatted_line: str
    status:         LineStatus
    checksum:       str


# ─── Diff ─────────────────────────────────────────────────────────────────────

class FormattingDiffResponse(BaseModel):
    diff_id:         str
    line_id:         str
    operation:       DiffOperationType
    status:          str              # "pending" | "accepted" | "rejected"
    raw_before:      str
    formatted_after: str


# ─── Format Request / Response ────────────────────────────────────────────────

class FormatBurstRequest(BaseModel):
    burst_id: int

class FormatBurstResponse(BaseModel):
    burst_id:     int
    lines:        List[BurstLineResponse]
    diffs:        List[FormattingDiffResponse]
    diff_count:   int
    processed_at: str


# ─── Diff Action ─────────────────────────────────────────────────────────────

class DiffActionRequest(BaseModel):
    diff_id: str

class DiffActionResponse(BaseModel):
    diff_id:               str
    status:                str
    line_id:               str
    updated_formatted_line: str


# ─── Bulk Action ─────────────────────────────────────────────────────────────

class BulkDiffActionRequest(BaseModel):
    burst_id: int

class BulkDiffActionResponse(BaseModel):
    updated_count: int
    diffs:         List[DiffActionResponse]


# ─── Formatted Burst Fetch ───────────────────────────────────────────────────

class FormattedBurstResponse(BaseModel):
    burst_id:       int
    has_formatting: bool
    lines:          List[BurstLineResponse]
    formatted_text: str
    raw_text:       str
```

---

## 5. SERVICE: `formatting/lexer_service.py`

Whitespace and unicode normalization. This is the first stage in the pipeline. It NEVER changes words.

```python
# services/formatting/lexer_service.py

"""
Lexical preprocessing for NotesFlare formatting pipeline.

ALLOWED:
- Normalize unicode (NFC normalization)
- Collapse multiple blank lines to maximum two
- Strip trailing whitespace per line
- Normalize Windows line endings to Unix

NOT ALLOWED:
- Spelling correction
- Abbreviation expansion
- Synonym replacement
- Any word-level changes
"""

import unicodedata
import re


def normalize_text(raw_text: str) -> str:
    """
    Apply all allowed lexical normalizations to raw burst text.
    Returns normalized text. Input is never mutated.
    """
    text = raw_text

    # 1. Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)

    # 2. Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Strip trailing whitespace per line (not leading — preserves indentation intent)
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 4. Collapse 3+ consecutive blank lines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def split_into_lines(normalized_text: str) -> list[str]:
    """
    Split normalized text into a list of lines.
    Returns empty strings for blank lines — preserves structure.
    """
    return normalized_text.split("\n")
```

---

## 6. SERVICE: `formatting/lineage_service.py`

Assigns stable UUIDs to every line in a burst. This is called once per burst before any diff is generated.

```python
# services/formatting/lineage_service.py

"""
Line identity management for NotesFlare V1.2.

Every line in a burst receives:
- A stable UUID (line_id)
- A SHA256 checksum of the raw content
- A line_index (position in burst)

These are stored in burst_lines and never reassigned.
If a burst is reformatted, existing line_ids are reused if the checksum matches.
New lines get new UUIDs.
"""

import uuid
import hashlib
from database.db import get_db
from datetime import datetime, timezone


def compute_checksum(raw_line: str) -> str:
    """SHA256 of the raw line content."""
    return hashlib.sha256(raw_line.encode("utf-8")).hexdigest()


def get_or_create_lines(burst_id: int, raw_lines: list[str]) -> list[dict]:
    """
    Given a burst_id and its current lines, return the stable line records.

    For each line:
    - If a burst_line exists at this index with the same checksum → reuse it
    - If checksum differs (line was edited) → create new entry, mark old as superseded
    - If no entry at this index → create new entry

    Returns a list of dicts matching the burst_lines table structure.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    existing = {
        row["line_index"]: dict(row)
        for row in db.execute(
            "SELECT * FROM burst_lines WHERE burst_id = ? ORDER BY line_index",
            (burst_id,),
        ).fetchall()
    }

    result = []

    for idx, raw_line in enumerate(raw_lines):
        checksum = compute_checksum(raw_line)

        if idx in existing and existing[idx]["checksum"] == checksum:
            # Reuse stable line
            result.append(existing[idx])
        else:
            # Create new line entry
            line_id = str(uuid.uuid4())
            db.execute(
                """
                INSERT INTO burst_lines
                    (line_id, burst_id, line_index, raw_line, formatted_line,
                     status, checksum, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'untouched', ?, ?, ?)
                """,
                (line_id, burst_id, idx, raw_line, raw_line, checksum, now, now),
            )
            _record_history(db, line_id, "create", {"index": idx, "checksum": checksum})
            result.append({
                "line_id": line_id,
                "burst_id": burst_id,
                "line_index": idx,
                "raw_line": raw_line,
                "formatted_line": raw_line,
                "status": "untouched",
                "checksum": checksum,
            })

    db.commit()
    return result


def _record_history(db, line_id: str, operation: str, detail: dict) -> None:
    """Insert an immutable history record for a line operation."""
    import json
    history_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO line_history (history_id, line_id, operation, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (history_id, line_id, operation, json.dumps(detail), now),
    )
```

---

## 7. SERVICE: `formatting/parser_service.py`

spaCy-based structural parsing. Returns sentence boundaries and structural signals per line. Loads the model once; reuses for all subsequent calls.

```python
# services/formatting/parser_service.py

"""
NLP structural parsing using spaCy.

Responsibilities:
- Sentence segmentation
- POS tagging (detect nouns, verbs, conjunctions)
- Dependency parsing (detect enumerations, nested structures)
- Named entity preservation (protect product names: NotesFlare, MetaMorph, MiniLM, Burst)

IMPORTANT: Load the spaCy model ONCE at module level.
spaCy model loading is expensive (~300ms). Do not reload per request.
"""

import spacy
from functools import lru_cache

# Protected tokens — must NEVER be altered by formatting
PROTECTED_TOKENS = frozenset([
    "NotesFlare", "MetaMorph", "MiniLM", "Burst", "Flareon",
    "spaCy", "ONNX", "FastAPI", "SQLite",
])


@lru_cache(maxsize=1)
def _load_model():
    """Load spaCy model. Cached — only loads once per process."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        raise RuntimeError(
            "spaCy model 'en_core_web_sm' not found. "
            "Run: python -m spacy download en_core_web_sm"
        )


def parse_lines(lines: list[str]) -> list[dict]:
    """
    Parse a list of text lines and return structural signals per line.

    Returns a list of dicts:
    {
        "line_index": int,
        "text": str,
        "is_sentence_start": bool,
        "is_sentence_end": bool,
        "is_list_item_candidate": bool,   # Starts with dash, asterisk, number+dot
        "is_heading_candidate": bool,     # Short, no verb, title-case or all-caps
        "is_quote_candidate": bool,       # Starts with quote char or "said", "according to"
        "has_conjunction_start": bool,    # Starts with "and", "but", "or", "so", "yet"
        "token_count": int,
        "contains_protected_token": bool,
    }
    """
    nlp = _load_model()
    results = []

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            results.append(_empty_line_signal(idx, line))
            continue

        doc = nlp(stripped)
        signals = _extract_signals(idx, line, doc)
        results.append(signals)

    return results


def _empty_line_signal(idx: int, line: str) -> dict:
    return {
        "line_index": idx,
        "text": line,
        "is_sentence_start": False,
        "is_sentence_end": False,
        "is_list_item_candidate": False,
        "is_heading_candidate": False,
        "is_quote_candidate": False,
        "has_conjunction_start": False,
        "token_count": 0,
        "contains_protected_token": False,
    }


def _extract_signals(idx: int, line: str, doc) -> dict:
    import re

    stripped = line.strip()
    tokens = [t.text for t in doc if not t.is_space]
    token_count = len(tokens)
    first_token = tokens[0].lower() if tokens else ""

    # List item detection
    is_list = bool(re.match(r"^[-*•]\s", stripped)) or bool(re.match(r"^\d+[.)]\s", stripped))

    # Heading detection: short line (<= 6 tokens), no verb, ends without punctuation
    has_verb = any(t.pos_ in ("VERB", "AUX") for t in doc)
    is_heading = (
        token_count <= 6
        and not has_verb
        and not stripped.endswith((".", "?", "!"))
        and len(stripped) > 2
    )

    # Quote detection
    QUOTE_STARTERS = {"said", "according", "as", "quoted", "per"}
    is_quote = (
        stripped.startswith(('"', "'", "\u201c", "\u2018"))
        or first_token in QUOTE_STARTERS
    )

    # Conjunction start
    CONJUNCTIONS = {"and", "but", "or", "so", "yet", "nor", "for"}
    has_conj_start = first_token in CONJUNCTIONS

    # Sentence boundary (spaCy sentence segmentation)
    sents = list(doc.sents)
    is_sent_start = len(sents) > 0
    is_sent_end = len(sents) > 0

    # Protected token check
    contains_protected = any(t.text in PROTECTED_TOKENS for t in doc)

    return {
        "line_index": idx,
        "text": line,
        "is_sentence_start": is_sent_start,
        "is_sentence_end": is_sent_end,
        "is_list_item_candidate": is_list,
        "is_heading_candidate": is_heading,
        "is_quote_candidate": is_quote,
        "has_conjunction_start": has_conj_start,
        "token_count": token_count,
        "contains_protected_token": contains_protected,
    }
```

---

## 8. SERVICE: `formatting/chunker_service.py`

Overlapping sliding window chunker. Operates on lines within a single burst.

```python
# services/formatting/chunker_service.py

"""
Chunking engine for NotesFlare V1.2.

Chunks exist ONLY inside bursts — never crossing burst boundaries.
Uses overlapping sliding windows to preserve semantic continuity.
"""

from typing import List


DEFAULT_CHUNK_SIZE = 800       # chars per chunk
DEFAULT_OVERLAP    = 150       # overlap between consecutive chunks


def chunk_lines(lines: list[str], chunk_size: int = DEFAULT_CHUNK_SIZE,
                overlap: int = DEFAULT_OVERLAP) -> list[dict]:
    """
    Split a list of lines into overlapping chunks.

    Returns a list of chunk dicts:
    {
        "chunk_index": int,
        "lines": list[str],
        "line_indices": list[int],   # Original line indices in burst
        "char_start": int,
        "char_end": int,
    }
    """
    if not lines:
        return []

    chunks = []
    current_chunk_lines = []
    current_chunk_indices = []
    current_chars = 0
    chunk_index = 0

    for line_idx, line in enumerate(lines):
        line_chars = len(line) + 1  # +1 for newline

        if current_chars + line_chars > chunk_size and current_chunk_lines:
            # Emit current chunk
            chunks.append(_make_chunk(chunk_index, current_chunk_lines, current_chunk_indices))
            chunk_index += 1

            # Start new chunk with overlap: keep last N chars worth of lines
            overlap_lines, overlap_indices = _trim_to_overlap(
                current_chunk_lines, current_chunk_indices, overlap
            )
            current_chunk_lines = overlap_lines + [line]
            current_chunk_indices = overlap_indices + [line_idx]
            current_chars = sum(len(l) + 1 for l in current_chunk_lines)
        else:
            current_chunk_lines.append(line)
            current_chunk_indices.append(line_idx)
            current_chars += line_chars

    if current_chunk_lines:
        chunks.append(_make_chunk(chunk_index, current_chunk_lines, current_chunk_indices))

    return chunks


def _make_chunk(index: int, lines: list[str], indices: list[int]) -> dict:
    text = "\n".join(lines)
    return {
        "chunk_index": index,
        "lines": lines,
        "line_indices": indices,
        "char_start": 0,   # Relative within chunk
        "char_end": len(text),
    }


def _trim_to_overlap(lines: list[str], indices: list[int], overlap: int) -> tuple:
    """Return the trailing portion of lines that fits within `overlap` chars."""
    kept_lines = []
    kept_indices = []
    total = 0
    for line, idx in zip(reversed(lines), reversed(indices)):
        total += len(line) + 1
        if total > overlap:
            break
        kept_lines.insert(0, line)
        kept_indices.insert(0, idx)
    return kept_lines, kept_indices
```

---

## 9. SERVICE: `formatting/embedding_service.py`

MiniLM sentence embeddings via ONNX Runtime. Used for semantic similarity and burst coherence. Lazy-loaded.

```python
# services/formatting/embedding_service.py

"""
Embedding engine using MiniLM via sentence-transformers + ONNX Runtime.

CPU-first. ONNX Runtime will automatically use GPU/NPU if available.
Model is loaded lazily on first call — startup is not delayed.

Used for:
- Semantic similarity between consecutive lines
- Burst cohesion scoring
- Topic transition detection (sudden similarity drop)
"""

from functools import lru_cache
from typing import List
import numpy as np


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model():
    """Load sentence-transformers model. Cached — only loads once per process."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)
        return model
    except ImportError:
        raise RuntimeError(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )


def embed_lines(lines: list[str]) -> np.ndarray:
    """
    Compute embeddings for a list of lines.
    Returns a 2D numpy array of shape (len(lines), embedding_dim).
    Empty lines get zero vectors.
    """
    model = _load_model()

    non_empty_indices = [i for i, l in enumerate(lines) if l.strip()]
    non_empty_lines = [lines[i] for i in non_empty_indices]

    if not non_empty_lines:
        return np.zeros((len(lines), 384))   # MiniLM embedding dim = 384

    embeddings = model.encode(non_empty_lines, convert_to_numpy=True)

    # Re-insert zero vectors for empty lines
    full_embeddings = np.zeros((len(lines), embeddings.shape[1]))
    for result_idx, orig_idx in enumerate(non_empty_indices):
        full_embeddings[orig_idx] = embeddings[result_idx]

    return full_embeddings


def compute_similarity_sequence(embeddings: np.ndarray) -> list[float]:
    """
    Compute cosine similarity between each consecutive pair of line embeddings.
    Returns a list of floats of length len(embeddings) - 1.
    A sudden drop indicates a topic transition boundary.
    """
    if len(embeddings) < 2:
        return []

    similarities = []
    for i in range(len(embeddings) - 1):
        a, b = embeddings[i], embeddings[i + 1]
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            similarities.append(0.0)
        else:
            similarities.append(float(np.dot(a, b) / (norm_a * norm_b)))

    return similarities
```

---

## 10. SERVICE: `formatting/formatter_service.py`

The rule-driven structural formatter. Takes parsed line signals and produces formatting operations. This is deterministic — no generative AI.

```python
# services/formatting/formatter_service.py

"""
Rule-driven structural formatter for NotesFlare V1.2.

This formatter is:
- Rule-based (no LLM, no generative model)
- Structural only (paragraph breaks, lists, headings, quotes)
- Non-destructive (never changes words)
- Operation-emitting (returns operations, not rewritten text)

Input:  list of line signals from parser_service
Output: list of formatting operations
"""

from typing import List


# Minimum token count before a line qualifies for heading detection
HEADING_MAX_TOKENS = 7

# Similarity threshold below which a paragraph break is suggested
TOPIC_BREAK_THRESHOLD = 0.45


def generate_operations(
    line_signals: list[dict],
    similarity_scores: list[float] | None = None,
) -> list[dict]:
    """
    Given NLP line signals (from parser_service) and optional similarity scores
    (from embedding_service), return a list of formatting operations.

    Each operation dict:
    {
        "line_index": int,
        "operation": str,          # DiffOperationType value
        "raw_before": str,
        "formatted_after": str,
    }
    """
    operations = []

    for i, signal in enumerate(line_signals):
        line = signal["text"]

        # Skip empty lines
        if not signal["token_count"]:
            continue

        # Never touch protected tokens lines
        if signal["contains_protected_token"] and signal["token_count"] <= 2:
            continue

        # ── List item formatting ──────────────────────────────────────────────
        if signal["is_list_item_candidate"]:
            formatted = _format_list_item(line)
            if formatted != line:
                operations.append({
                    "line_index": i,
                    "operation": "format_as_list_item",
                    "raw_before": line,
                    "formatted_after": formatted,
                })
            continue

        # ── Heading formatting ────────────────────────────────────────────────
        if signal["is_heading_candidate"] and signal["token_count"] <= HEADING_MAX_TOKENS:
            formatted = _format_heading(line)
            if formatted != line:
                operations.append({
                    "line_index": i,
                    "operation": "format_as_heading",
                    "raw_before": line,
                    "formatted_after": formatted,
                })
            continue

        # ── Quote formatting ──────────────────────────────────────────────────
        if signal["is_quote_candidate"]:
            formatted = _format_quote(line)
            if formatted != line:
                operations.append({
                    "line_index": i,
                    "operation": "format_as_quote",
                    "raw_before": line,
                    "formatted_after": formatted,
                })
            continue

        # ── Paragraph break insertion ─────────────────────────────────────────
        # Insert a paragraph break BEFORE this line if:
        # (a) embedding similarity with previous non-empty line is below threshold
        # (b) or the line starts with a discourse conjunction after a long line
        if similarity_scores and i > 0 and i - 1 < len(similarity_scores):
            if similarity_scores[i - 1] < TOPIC_BREAK_THRESHOLD:
                operations.append({
                    "line_index": i,
                    "operation": "insert_paragraph_break",
                    "raw_before": line,
                    "formatted_after": "\n" + line,
                })
                continue

        if signal["has_conjunction_start"] and i > 0:
            prev = line_signals[i - 1]
            if prev["token_count"] > 12:
                operations.append({
                    "line_index": i,
                    "operation": "insert_paragraph_break",
                    "raw_before": line,
                    "formatted_after": "\n" + line,
                })

    return operations


def _format_list_item(line: str) -> str:
    """Normalize list item: ensure bullet is "- " prefix."""
    import re
    stripped = line.strip()
    # Already has dash bullet
    if stripped.startswith("- "):
        return stripped
    # Has asterisk or dot bullet
    if re.match(r"^[*•]\s", stripped):
        return "- " + stripped[2:]
    # Has numbered item
    if re.match(r"^\d+[.)]\s", stripped):
        return stripped
    return line


def _format_heading(line: str) -> str:
    """Title-case a heading candidate if it isn't already."""
    stripped = line.strip()
    if stripped == stripped.upper() and len(stripped) > 2:
        return stripped.title()
    return stripped.title() if stripped != stripped.title() else stripped


def _format_quote(line: str) -> str:
    """Ensure quote uses typographic quote chars."""
    stripped = line.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        return "\u201c" + stripped[1:-1] + "\u201d"
    return stripped
```

---

## 11. SERVICE: `formatting/diff_service.py`

Stores and retrieves formatting diffs. Handles accept/reject logic.

```python
# services/formatting/diff_service.py

"""
Diff storage and action service for NotesFlare V1.2.

Stores formatting operations as diffs in burst_diffs.
Handles accept/reject and bulk actions.
Updates burst_lines.status on accept/reject.
Records line_history on every state change.
"""

import uuid
import json
from datetime import datetime, timezone
from database.db import get_db


def store_diffs(burst_id: int, line_records: list[dict], operations: list[dict]) -> list[dict]:
    """
    Given a list of line records and formatting operations, create diff rows.

    Clears any existing PENDING diffs for this burst before inserting new ones.
    Does NOT clear ACCEPTED or REJECTED diffs — those are permanent history.

    Returns the list of created diff dicts.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Delete pending diffs only (do not touch accepted/rejected)
    db.execute(
        "DELETE FROM burst_diffs WHERE burst_id = ? AND status = 'pending'",
        (burst_id,)
    )

    # Build a lookup from line_index → line_id
    index_to_line = {r["line_index"]: r for r in line_records}

    created = []
    for op in operations:
        line_idx = op["line_index"]
        if line_idx not in index_to_line:
            continue

        line_record = index_to_line[line_idx]
        diff_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO burst_diffs
                (diff_id, burst_id, line_id, operation, status,
                 raw_before, formatted_after, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """,
            (
                diff_id, burst_id, line_record["line_id"],
                op["operation"], op["raw_before"], op["formatted_after"],
                now, now,
            )
        )

        # Mark the line as pending
        db.execute(
            "UPDATE burst_lines SET status = 'pending', updated_at = ? WHERE line_id = ?",
            (now, line_record["line_id"])
        )

        created.append({
            "diff_id": diff_id,
            "burst_id": burst_id,
            "line_id": line_record["line_id"],
            "operation": op["operation"],
            "status": "pending",
            "raw_before": op["raw_before"],
            "formatted_after": op["formatted_after"],
        })

    db.commit()
    return created


def get_diffs_for_burst(burst_id: int) -> list[dict]:
    """Return all diffs for a burst ordered by creation time."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM burst_diffs WHERE burst_id = ? ORDER BY created_at ASC",
        (burst_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def accept_diff(diff_id: str) -> dict:
    """Accept a single diff. Updates burst_lines.formatted_line and status."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    diff = db.execute(
        "SELECT * FROM burst_diffs WHERE diff_id = ?", (diff_id,)
    ).fetchone()
    if not diff:
        raise ValueError(f"Diff {diff_id} not found.")

    diff = dict(diff)

    db.execute(
        "UPDATE burst_diffs SET status = 'accepted', updated_at = ? WHERE diff_id = ?",
        (now, diff_id)
    )
    db.execute(
        """
        UPDATE burst_lines
        SET status = 'accepted', formatted_line = ?, updated_at = ?
        WHERE line_id = ?
        """,
        (diff["formatted_after"], now, diff["line_id"])
    )
    _record_history(db, diff["line_id"], "accept", {"diff_id": diff_id})
    db.commit()

    return {
        "diff_id": diff_id,
        "status": "accepted",
        "line_id": diff["line_id"],
        "updated_formatted_line": diff["formatted_after"],
    }


def reject_diff(diff_id: str) -> dict:
    """Reject a single diff. Restores formatted_line to raw_line."""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    diff = db.execute(
        "SELECT * FROM burst_diffs WHERE diff_id = ?", (diff_id,)
    ).fetchone()
    if not diff:
        raise ValueError(f"Diff {diff_id} not found.")

    diff = dict(diff)

    db.execute(
        "UPDATE burst_diffs SET status = 'rejected', updated_at = ? WHERE diff_id = ?",
        (now, diff_id)
    )
    db.execute(
        """
        UPDATE burst_lines
        SET status = 'rejected', formatted_line = raw_line, updated_at = ?
        WHERE line_id = ?
        """,
        (now, diff["line_id"])
    )
    _record_history(db, diff["line_id"], "reject", {"diff_id": diff_id})
    db.commit()

    # Get updated raw_line for response
    line = db.execute(
        "SELECT raw_line FROM burst_lines WHERE line_id = ?", (diff["line_id"],)
    ).fetchone()

    return {
        "diff_id": diff_id,
        "status": "rejected",
        "line_id": diff["line_id"],
        "updated_formatted_line": dict(line)["raw_line"],
    }


def accept_all_pending(burst_id: int) -> list[dict]:
    """Accept all pending diffs for a burst."""
    db = get_db()
    pending = db.execute(
        "SELECT diff_id FROM burst_diffs WHERE burst_id = ? AND status = 'pending'",
        (burst_id,)
    ).fetchall()
    results = []
    for row in pending:
        results.append(accept_diff(row["diff_id"]))
    return results


def reject_all_pending(burst_id: int) -> list[dict]:
    """Reject all pending diffs for a burst."""
    db = get_db()
    pending = db.execute(
        "SELECT diff_id FROM burst_diffs WHERE burst_id = ? AND status = 'pending'",
        (burst_id,)
    ).fetchall()
    results = []
    for row in pending:
        results.append(reject_diff(row["diff_id"]))
    return results


def get_formatted_burst(burst_id: int, raw_text: str) -> dict:
    """
    Return the formatted text for a burst by applying all accepted diffs.
    Falls back to raw text if no accepted diffs exist.
    """
    db = get_db()
    lines_rows = db.execute(
        "SELECT * FROM burst_lines WHERE burst_id = ? ORDER BY line_index",
        (burst_id,)
    ).fetchall()

    if not lines_rows:
        return {
            "burst_id": burst_id,
            "has_formatting": False,
            "lines": [],
            "formatted_text": raw_text,
            "raw_text": raw_text,
        }

    lines = [dict(r) for r in lines_rows]
    has_accepted = any(l["status"] == "accepted" for l in lines)

    formatted_text = "\n".join(l["formatted_line"] for l in lines)

    return {
        "burst_id": burst_id,
        "has_formatting": has_accepted,
        "lines": lines,
        "formatted_text": formatted_text,
        "raw_text": raw_text,
    }


def _record_history(db, line_id: str, operation: str, detail: dict) -> None:
    import uuid as _uuid
    history_id = str(_uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO line_history (history_id, line_id, operation, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (history_id, line_id, operation, json.dumps(detail), now),
    )
```

---

## 12. NEW API ROUTES: `api/formatting_routes.py`

```python
# api/formatting_routes.py

from fastapi import APIRouter, HTTPException
from models.formatting_schemas import (
    FormatBurstRequest, FormatBurstResponse,
    BurstLineResponse, FormattingDiffResponse,
    DiffActionRequest, DiffActionResponse,
    BulkDiffActionRequest, BulkDiffActionResponse,
    FormattedBurstResponse,
)
from services import stream_service
from services.formatting import (
    lexer_service, parser_service, chunker_service,
    embedding_service, formatter_service, diff_service, lineage_service,
)
from datetime import datetime, timezone

formatting_router = APIRouter(prefix="/format")


@formatting_router.post("/burst", response_model=FormatBurstResponse)
def format_burst(body: FormatBurstRequest):
    """
    Run the formatting pipeline on a burst.

    Pipeline stages:
    1. Reconstruct raw text from burst_entries
    2. Lexical normalization
    3. Line splitting + stable ID assignment
    4. spaCy NLP parsing
    5. Chunking
    6. Embedding (semantic similarity)
    7. Rule-driven operation generation
    8. Diff storage (replaces pending diffs only)

    Returns all lines and diffs for the burst.
    """
    burst_id = body.burst_id

    # Stage 1: Reconstruct raw text
    raw_text = stream_service.reconstruct_burst(burst_id)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Burst is empty — nothing to format.")

    # Stage 2: Lexical normalization
    normalized = lexer_service.normalize_text(raw_text)
    raw_lines = lexer_service.split_into_lines(normalized)

    # Stage 3: Stable line IDs
    line_records = lineage_service.get_or_create_lines(burst_id, raw_lines)

    # Stage 4: NLP parsing
    line_signals = parser_service.parse_lines(raw_lines)

    # Stage 5: Chunking (used for embedding coherence)
    chunks = chunker_service.chunk_lines(raw_lines)

    # Stage 6: Embeddings + similarity (only if lines exist)
    similarity_scores = None
    if len(raw_lines) > 1:
        try:
            embeddings = embedding_service.embed_lines(raw_lines)
            similarity_scores = embedding_service.compute_similarity_sequence(embeddings)
        except Exception as e:
            # Embedding is optional — fall back to rule-only formatting
            print(f"[format_burst] Embedding skipped: {e}")

    # Stage 7: Generate formatting operations
    operations = formatter_service.generate_operations(line_signals, similarity_scores)

    # Stage 8: Store diffs
    diffs = diff_service.store_diffs(burst_id, line_records, operations)

    return FormatBurstResponse(
        burst_id=burst_id,
        lines=[BurstLineResponse(**l) for l in line_records],
        diffs=[FormattingDiffResponse(**d) for d in diffs],
        diff_count=len(diffs),
        processed_at=datetime.now(timezone.utc).isoformat(),
    )


@formatting_router.post("/diff/accept", response_model=DiffActionResponse)
def accept_diff(body: DiffActionRequest):
    """Accept a single formatting diff."""
    try:
        result = diff_service.accept_diff(body.diff_id)
        return DiffActionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@formatting_router.post("/diff/reject", response_model=DiffActionResponse)
def reject_diff(body: DiffActionRequest):
    """Reject a single formatting diff."""
    try:
        result = diff_service.reject_diff(body.diff_id)
        return DiffActionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@formatting_router.post("/diff/accept-all", response_model=BulkDiffActionResponse)
def accept_all_diffs(body: BulkDiffActionRequest):
    """Accept all pending diffs for a burst."""
    results = diff_service.accept_all_pending(body.burst_id)
    return BulkDiffActionResponse(
        updated_count=len(results),
        diffs=[DiffActionResponse(**r) for r in results],
    )


@formatting_router.post("/diff/reject-all", response_model=BulkDiffActionResponse)
def reject_all_diffs(body: BulkDiffActionRequest):
    """Reject all pending diffs for a burst."""
    results = diff_service.reject_all_pending(body.burst_id)
    return BulkDiffActionResponse(
        updated_count=len(results),
        diffs=[DiffActionResponse(**r) for r in results],
    )


@formatting_router.get("/burst/{burst_id}", response_model=FormattedBurstResponse)
def get_formatted_burst(burst_id: int):
    """
    Return the formatted version of a burst.
    If no accepted diffs exist, returns raw text with has_formatting=False.
    """
    raw_text = stream_service.reconstruct_burst(burst_id)
    result = diff_service.get_formatted_burst(burst_id, raw_text)
    return FormattedBurstResponse(
        burst_id=result["burst_id"],
        has_formatting=result["has_formatting"],
        lines=[BurstLineResponse(**l) for l in result["lines"]],
        formatted_text=result["formatted_text"],
        raw_text=result["raw_text"],
    )
```

---

## 13. REGISTER ROUTES IN `main.py`

Add these two lines to `main.py`. Do not modify anything else in `main.py`.

```python
# In main.py — add after existing router includes:

from api.formatting_routes import formatting_router

# In the app setup section (after `app.include_router(router, prefix="/api")`):
app.include_router(formatting_router, prefix="/api")
```

---

## 14. UPDATED `requirements.txt`

```
# ─── V1 / V1.1 (unchanged) ───────────────────────────────────────────────────
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
freezegun>=1.4.0
pytest-cov>=4.1.0

# ─── V1.2 NLP (new) ──────────────────────────────────────────────────────────
spacy>=3.7.0
sentence-transformers>=2.7.0
onnxruntime>=1.18.0
numpy>=1.26.0
```

After updating, run:

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

## 15. UPDATED API CONTRACT SUMMARY

All V1 and V1.1 endpoints remain unchanged. New V1.2 endpoints:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/format/burst` | Run formatting pipeline on a burst |
| POST | `/api/format/diff/accept` | Accept a single diff |
| POST | `/api/format/diff/reject` | Reject a single diff |
| POST | `/api/format/diff/accept-all` | Accept all pending diffs for a burst |
| POST | `/api/format/diff/reject-all` | Reject all pending diffs for a burst |
| GET | `/api/format/burst/{id}` | Fetch formatted burst content |

---

## 16. IMPLEMENTATION ORDER AND VERIFICATION

### Step 1 — Dependencies + spaCy model
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -c "import spacy; spacy.load('en_core_web_sm'); print('spaCy OK')"
python -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers OK')"
```

### Step 2 — Schema migration
```bash
python main.py
# Must start without errors
# GET /api/health → {"status": "ok"}
# SQLite inspector: SELECT name FROM sqlite_master WHERE type='table';
# Must show: burst_lines, burst_diffs, line_history
```

### Step 3 — New Pydantic schemas
```bash
python -c "from models.formatting_schemas import FormatBurstResponse; print('schemas OK')"
```

### Step 4 — Formatting services (in order)
```bash
python -c "from services.formatting.lexer_service import normalize_text; print(normalize_text('hello\n\n\n\nworld'))"
python -c "from services.formatting.parser_service import parse_lines; r = parse_lines(['Hello world', 'another line']); print('parser OK:', len(r), 'signals')"
python -c "from services.formatting.chunker_service import chunk_lines; print('chunker OK:', chunk_lines(['a','b','c']))"
python -c "from services.formatting.embedding_service import embed_lines; import numpy as np; e = embed_lines(['Hello world']); print('embeddings OK, shape:', e.shape)"
```

### Step 5 — Full pipeline end-to-end
```bash
# POST /api/format/burst with {"burst_id": 1}
# Must return: {"burst_id": 1, "lines": [...], "diffs": [...], "diff_count": N, "processed_at": "..."}
```

### Step 6 — Accept/Reject
```bash
# POST /api/format/diff/accept with {"diff_id": "<from previous step>"}
# Must return: {"diff_id": "...", "status": "accepted", ...}
# GET /api/format/burst/1
# Must return: {"has_formatting": true, "formatted_text": "..."}
```

### Step 7 — Full regression
```bash
GET /api/health          → {"status": "ok"}
GET /api/session/resume  → valid session
POST /api/burst/append   → valid append
GET /api/flareons        → list of flareons
```

---

## 17. COMMON MISTAKES TO AVOID

**Do not:**
- Modify `burst_entries` table — it remains the source of truth for raw text
- Run formatting automatically — it must ONLY run when `POST /api/format/burst` is called
- Load spaCy or SentenceTransformer at import time in `main.py` — lazy load via `@lru_cache`
- Raise HTTP errors when embedding fails — embedding is optional; fall back gracefully
- Clear ACCEPTED or REJECTED diffs when re-formatting — only clear PENDING

**Do:**
- Always reconstruct raw text from `stream_service.reconstruct_burst()` before formatting
- Use `lru_cache` for model loading — models load once per process
- Record every accept/reject in `line_history` — this is the audit trail
- Return `diff_count: 0` (not an error) when the burst has no structural changes to propose
