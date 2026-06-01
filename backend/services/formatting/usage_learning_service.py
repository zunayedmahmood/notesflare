# services/formatting/usage_learning_service.py

"""
Usage-learning layer for NotesFlare structural stabilisation.

This module turns accepted structural diffs into future formatter hints. It is
intentionally conservative:
- every accept/reject decision is logged as usage evidence
- ONLY accepted diffs update the stabilisation profile
- rejected diffs are never learned from, because accidental rejection should not
  poison future behaviour
- the profile remains generic JSON, so this is a study-of-old-data mechanism,
  not a user-facing feature or model trainer
"""

from __future__ import annotations

import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from database.db import get_db
from services.formatting.stabilisation_profile_service import (
    STORAGE_PROFILE,
    reset_profile_cache,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’._+-]*")
_BULLET_RE = re.compile(r"^\s*-\s+(.+?)\s*$")
_CAMEL_OR_MIXED_RE = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])[A-Za-z0-9][A-Za-z0-9._+-]*$")
KNOWN_SHORT_TOKENS = {
    "np", "rn", "asap", "eta", "mvp", "api", "db", "ui", "ux", "nlp", "llm",
    "ocr", "rag", "cpu", "gpu", "sla", "kpi", "qa", "pr", "jwt", "sku", "pos",
    "n3", "n4", "n5", "jlpt", "mext", "visa", "cv", "sop", "gpa", "todo",
}
CONNECTOR_WORDS = {"and", "or", "plus", "then", "also", "with"}


def ensure_usage_tables() -> None:
    """Create usage-learning tables if the current DB is older than this module."""
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS stabilisation_usage_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id        TEXT NOT NULL UNIQUE,
            diff_id         TEXT,
            burst_id        INTEGER,
            line_id         TEXT,
            operation       TEXT NOT NULL,
            decision        TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected')),
            learned         INTEGER NOT NULL DEFAULT 0,
            raw_before      TEXT NOT NULL DEFAULT '',
            formatted_after TEXT NOT NULL DEFAULT '',
            features_json   TEXT NOT NULL DEFAULT '{}',
            profile_path    TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_stabilisation_usage_decision
            ON stabilisation_usage_events(decision, operation, created_at);

        CREATE TABLE IF NOT EXISTS stabilisation_profile_events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_event_id TEXT NOT NULL UNIQUE,
            usage_event_id TEXT NOT NULL,
            learned_json   TEXT NOT NULL DEFAULT '{}',
            profile_path   TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    db.commit()


def record_diff_decision(diff: dict[str, Any], decision: str) -> dict[str, Any]:
    """
    Track accept/reject for a diff. Only accepted diffs mutate the profile.
    """
    if decision not in {"accepted", "rejected"}:
        raise ValueError("decision must be 'accepted' or 'rejected'")

    ensure_usage_tables()
    features = extract_features_from_diff(diff)
    learned_payload: dict[str, Any] = {}
    learned = 0
    profile_path = _resolve_profile_path()

    if decision == "accepted":
        learned_payload = update_profile_from_accepted_diff(diff, features, profile_path)
        learned = 1 if learned_payload.get("changed") else 0

    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    db.execute(
        """
        INSERT INTO stabilisation_usage_events
            (event_id, diff_id, burst_id, line_id, operation, decision, learned,
             raw_before, formatted_after, features_json, profile_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            diff.get("diff_id"),
            diff.get("burst_id"),
            diff.get("line_id"),
            diff.get("operation", "unknown"),
            decision,
            learned,
            diff.get("raw_before", ""),
            diff.get("formatted_after", ""),
            json.dumps(features, ensure_ascii=False, sort_keys=True),
            str(profile_path),
            now,
        ),
    )

    if learned_payload:
        db.execute(
            """
            INSERT INTO stabilisation_profile_events
                (profile_event_id, usage_event_id, learned_json, profile_path, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                event_id,
                json.dumps(learned_payload, ensure_ascii=False, sort_keys=True),
                str(profile_path),
                now,
            ),
        )
    db.commit()
    return {"event_id": event_id, "decision": decision, "learned": bool(learned), "features": features}


def extract_features_from_diff(diff: dict[str, Any]) -> dict[str, Any]:
    """Extract generic structural signals from a diff for profile learning."""
    operation = str(diff.get("operation", ""))
    raw = str(diff.get("raw_before", ""))
    formatted = str(diff.get("formatted_after", ""))
    text = f"{raw}\n{formatted}"

    bullet_items = _extract_bullet_items(formatted)
    list_header = _extract_list_header(formatted)
    short_tokens = _extract_short_tokens(text)
    protected_terms = _extract_protected_terms(text)
    # Do not learn bullet first-words as discourse break starters. In a
    # continuous-list diff, newlines are list structure, not paragraph-boundary
    # evidence.
    break_starters = [] if bullet_items or list_header else _extract_break_starters(formatted)

    phrase_candidates: list[str] = []
    if operation == "format_as_list_item":
        item = formatted.strip()[2:].strip() if formatted.strip().startswith("- ") else raw.strip()
        phrase_candidates.append(item)
    phrase_candidates.extend(bullet_items)

    # When a continuous list conversion preserved gap text as a bullet item, those
    # bullets are the best signal for future one-line list recognition.
    phrase_candidates = [_clean_phrase(item) for item in phrase_candidates]
    phrase_candidates = [item for item in phrase_candidates if _is_learnable_phrase(item)]

    return {
        "operation": operation,
        "list_header": list_header,
        "phrase_candidates": _unique(phrase_candidates),
        "short_tokens": _unique(short_tokens),
        "protected_terms": _unique(protected_terms),
        "compound_terms": _extract_compound_terms(phrase_candidates),
        "break_starters": _unique(break_starters),
    }


def update_profile_from_accepted_diff(
    diff: dict[str, Any],
    features: dict[str, Any] | None = None,
    profile_path: Path | None = None,
) -> dict[str, Any]:
    """Update the file-backed stabilisation profile using accepted diff features."""
    features = features or extract_features_from_diff(diff)
    profile_path = profile_path or _resolve_profile_path()
    profile = _load_profile(profile_path)
    profile.setdefault("version", 1)
    profile.setdefault("profile_name", "notesflare-learned-user-profile")
    profile.setdefault("formatting_preferences", {})
    profile.setdefault("learned_from_accepts", {})

    learned = profile["learned_from_accepts"]
    learned.setdefault("accepted_operations", {})
    learned.setdefault("continuous_list_headers", {})
    learned.setdefault("continuous_list_item_phrases", {})
    learned.setdefault("short_tokens", {})
    learned.setdefault("protected_terms", {})
    learned.setdefault("break_starters", {})

    changed = False
    operation = features.get("operation") or diff.get("operation", "unknown")
    changed |= _increment_counter(learned["accepted_operations"], str(operation))

    header = features.get("list_header")
    if header:
        changed |= _increment_counter(learned["continuous_list_headers"], str(header).lower())
        changed |= _append_unique(profile, "continuous_list_headers", str(header).lower())
        changed |= _append_unique(profile, "list_header_words", str(header).lower())

    for phrase in features.get("phrase_candidates", []):
        changed |= _increment_counter(learned["continuous_list_item_phrases"], phrase)
        changed |= _append_unique(profile, "continuous_list_item_phrases", phrase)
        for pair in _phrase_to_compound_pairs(phrase):
            changed |= _append_compound(profile, pair)

    for token in features.get("short_tokens", []):
        changed |= _increment_counter(learned["short_tokens"], token.lower())
        changed |= _append_unique(profile, "short_tokens", token)

    for term in features.get("protected_terms", []):
        changed |= _increment_counter(learned["protected_terms"], term)
        changed |= _append_unique(profile, "protected_terms", term)

    for starter in features.get("break_starters", []):
        changed |= _increment_counter(learned["break_starters"], starter)
        changed |= _append_unique(profile, "break_starters", starter)

    changed |= _update_preferences_from_accepts(profile)

    if changed:
        profile["updated_at"] = datetime.now(timezone.utc).isoformat()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        reset_profile_cache()

    return {
        "changed": changed,
        "profile_path": str(profile_path),
        "learned_from": features,
        "preferences": profile.get("formatting_preferences", {}),
    }


def study_accepted_usage(profile_path: Path | None = None) -> dict[str, Any]:
    """Rebuild/update the profile from old accepted usage events in the DB."""
    ensure_usage_tables()
    db = get_db()
    rows = db.execute(
        """
        SELECT raw_before, formatted_after, operation, diff_id, burst_id, line_id
        FROM stabilisation_usage_events
        WHERE decision = 'accepted'
        ORDER BY created_at ASC, id ASC
        """
    ).fetchall()

    profile_path = profile_path or _resolve_profile_path()
    applied = 0
    for row in rows:
        payload = dict(row)
        update = update_profile_from_accepted_diff(payload, profile_path=profile_path)
        if update.get("changed"):
            applied += 1
    return {"accepted_events_seen": len(rows), "profile_updates_applied": applied, "profile_path": str(profile_path)}


def _resolve_profile_path() -> Path:
    env_path = os.getenv("NOTESFLARE_STABILISATION_PROFILE")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return STORAGE_PROFILE


def _load_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_bullet_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        match = _BULLET_RE.match(line)
        if match:
            items.append(_clean_phrase(match.group(1)))
    return [item for item in items if item]


def _extract_list_header(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    if lines[0].endswith(":") and any(_BULLET_RE.match(line) for line in lines[1:]):
        return _clean_word(lines[0][:-1])
    return None


def _extract_short_tokens(text: str) -> list[str]:
    tokens = []
    for token in _WORD_RE.findall(text):
        clean = _clean_word(token)
        if not clean or clean in CONNECTOR_WORDS:
            continue
        if clean in KNOWN_SHORT_TOKENS or len(clean) <= 2 or (token.isupper() and len(token) <= 5):
            tokens.append(token)
    return tokens


def _extract_protected_terms(text: str) -> list[str]:
    terms = []
    for token in _WORD_RE.findall(text):
        stripped = token.strip("'’\".,;:!?()[]{}<> ")
        if len(stripped) >= 4 and _CAMEL_OR_MIXED_RE.match(stripped):
            terms.append(stripped)
    return terms


def _extract_break_starters(formatted: str) -> list[str]:
    starters = []
    for marker in ("\n\n", "\n"):
        if marker in formatted:
            parts = formatted.split(marker)
            for part in parts[1:]:
                words = _WORD_RE.findall(part.strip())
                if words:
                    starter = _clean_word(words[0])
                    if starter not in CONNECTOR_WORDS and len(starter) >= 3:
                        starters.append(starter)
    return starters


def _extract_compound_terms(phrases: list[str]) -> list[list[str]]:
    pairs: list[list[str]] = []
    for phrase in phrases:
        pairs.extend(_phrase_to_compound_pairs(phrase))
    return pairs


def _phrase_to_compound_pairs(phrase: str) -> list[list[str]]:
    words = [_clean_word(w) for w in _WORD_RE.findall(phrase)]
    if len(words) < 2:
        return []
    if len(words) == 2:
        return [[words[0], words[1]]]
    return [[words[i], words[i + 1]] for i in range(len(words) - 1)]


def _clean_phrase(text: str) -> str:
    return " ".join(_clean_word(w) for w in _WORD_RE.findall(text) if _clean_word(w))


def _clean_word(text: str) -> str:
    return text.strip("'’\".,;:!?()[]{}<> ").lower()


def _is_learnable_phrase(phrase: str) -> bool:
    if not phrase:
        return False
    if phrase in CONNECTOR_WORDS:
        return False
    words = phrase.split()
    return 1 <= len(words) <= 5


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _append_unique(profile: dict[str, Any], key: str, value: str) -> bool:
    if not value:
        return False
    profile.setdefault(key, [])
    values = profile[key] if isinstance(profile[key], list) else []
    marker_values = {json.dumps(v, sort_keys=True, ensure_ascii=False).lower() for v in values}
    marker = json.dumps(value, sort_keys=True, ensure_ascii=False).lower()
    if marker in marker_values:
        return False
    values.append(value)
    profile[key] = values
    return True


def _append_compound(profile: dict[str, Any], pair: list[str]) -> bool:
    if len(pair) != 2 or not all(pair):
        return False
    profile.setdefault("compound_terms", [])
    values = profile["compound_terms"] if isinstance(profile["compound_terms"], list) else []
    normalized = [pair[0].lower(), pair[1].lower()]
    existing = {
        json.dumps(v, sort_keys=True, ensure_ascii=False).lower()
        for v in values
    }
    marker = json.dumps(normalized, sort_keys=True, ensure_ascii=False).lower()
    if marker in existing:
        return False
    values.append(normalized)
    profile["compound_terms"] = values
    return True


def _increment_counter(counter: dict[str, Any], key: str) -> bool:
    if not key:
        return False
    before = int(counter.get(key, 0) or 0)
    counter[key] = before + 1
    return True


def _update_preferences_from_accepts(profile: dict[str, Any]) -> bool:
    learned = profile.get("learned_from_accepts", {})
    ops = learned.get("accepted_operations", {}) if isinstance(learned, dict) else {}
    prefs = profile.setdefault("formatting_preferences", {})
    changed = False

    list_accepts = int(ops.get("format_as_list_item", 0) or 0)
    line_accepts = int(ops.get("insert_line_break", 0) or 0)
    heading_accepts = int(ops.get("format_as_heading", 0) or 0)

    if list_accepts >= 12 and prefs.get("listing_aggressiveness") != "aggressive":
        prefs["listing_aggressiveness"] = "aggressive"
        changed = True
    elif list_accepts >= 4 and not prefs.get("listing_aggressiveness"):
        prefs["listing_aggressiveness"] = "moderate"
        changed = True

    if line_accepts >= 20 and prefs.get("line_break_aggressiveness") != "aggressive":
        prefs["line_break_aggressiveness"] = "aggressive"
        changed = True
    elif line_accepts >= 6 and not prefs.get("line_break_aggressiveness"):
        prefs["line_break_aggressiveness"] = "balanced"
        changed = True

    if heading_accepts < 5 and prefs.get("heading_aggressiveness") != "conservative":
        prefs["heading_aggressiveness"] = "conservative"
        changed = True

    prefs.setdefault("paragraph_density", "balanced")
    prefs.setdefault("heading_aggressiveness", "conservative")
    prefs.setdefault("listing_aggressiveness", "moderate")
    prefs.setdefault("line_break_aggressiveness", "balanced")
    return changed
