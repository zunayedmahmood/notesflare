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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    burst_id    INTEGER NOT NULL UNIQUE REFERENCES bursts(id) ON DELETE CASCADE,
    content     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_state (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    last_opened_flareon_id  INTEGER REFERENCES flareons(id),
    last_opened_burst_id    INTEGER REFERENCES bursts(id),
    last_active_at          TEXT
);

-- Seed one app_state row that always exists
INSERT OR IGNORE INTO app_state (id) VALUES (1);
