-- schema.sql

CREATE TABLE IF NOT EXISTS flareons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    last_opened_at TEXT
);

CREATE TABLE IF NOT EXISTS bursts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flareon_id  INTEGER NOT NULL REFERENCES flareons(id) ON DELETE CASCADE,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS burst_entries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    burst_id         INTEGER NOT NULL REFERENCES bursts(id) ON DELETE CASCADE,
    content_chunk    TEXT    NOT NULL DEFAULT '',
    sequence_number  INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_state (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    last_opened_flareon_id  INTEGER REFERENCES flareons(id),
    last_opened_burst_id    INTEGER REFERENCES bursts(id),
    last_active_at          TEXT
);

-- Seed one app_state row that always exists
INSERT OR IGNORE INTO app_state (id) VALUES (1);

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
