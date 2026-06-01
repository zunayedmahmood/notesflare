# services/formatting/stabilisation_profile_service.py

"""
Dynamic stabilisation profile for NotesFlare's deterministic formatter.

This is intentionally file-backed instead of UI-backed for now. It gives the
NLP pipeline a hidden, local-first way to adapt to user/domain vocabulary and
formatting preferences without adding a visible settings surface.

Load order:
1. NOTESFLARE_STABILISATION_PROFILE env var, if set
2. storage/stabilisation_profile.json, if present
3. StabilisationModule/stabilisation_profile.default.json
4. built-in defaults below
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
STORAGE_PROFILE = PROJECT_ROOT / "storage" / "stabilisation_profile.json"
MODULE_DEFAULT_PROFILE = PROJECT_ROOT / "StabilisationModule" / "stabilisation_profile.default.json"


BUILTIN_PROFILE: dict[str, Any] = {
    "version": 1,
    "profile_name": "default-balanced",
    "formatting_preferences": {
        "paragraph_density": "balanced",       # longer | balanced | shorter
        "line_break_aggressiveness": "balanced", # conservative | balanced | aggressive
        "listing_aggressiveness": "moderate",    # conservative | moderate | aggressive
        "heading_aggressiveness": "conservative",
    },
    "short_tokens": [
        "np", "rn", "asap", "btw", "tbh", "imo", "idk", "todo", "ETA", "MVP",
        "API", "DB", "UI", "UX", "NLP", "LLM", "OCR", "RAG", "CPU", "GPU",
    ],
    "protected_terms": [
        "NotesFlare", "MetaMorph", "MiniLM", "Burst", "Flareon", "spaCy", "ONNX",
        "FastAPI", "SQLite", "Next.js", "React", "Electron",
    ],
    "list_header_words": [
        "need", "needs", "todo", "todos", "tasks", "ideas", "points", "questions",
        "issues", "problems", "steps", "features", "include", "includes",
        "requirements", "check", "checks", "remember", "focus", "plan", "plans",
        "try", "tries", "fix", "fixes", "add", "adds", "compare", "review",
    ],
    "continuous_list_headers": [
        "need", "todo", "tasks", "ideas", "questions", "steps", "features", "fix",
        "add", "check", "review", "compare", "include", "remember", "focus",
    ],
    "continuous_list_item_phrases": [
        "raw note fidelity", "query drift", "chunking", "semantic chunking", "semantic search",
        "embedding cache", "vector storage", "burst indexing", "boundary quality",
        "formatting latency", "reader trust", "model comparison", "ablation study",
        "evidence chain", "citation mapping", "annotation quality", "retrieval latency",
        "false positives", "evaluation metric", "literature review", "method section",
        "paper structure", "review comments", "dataset bias", "user profile", "short tokens",
        "protected terms", "local storage", "diff review", "accept reject", "benchmark loop",
        "line breaks", "list detection", "quote detection", "heading detection", "sqlite first",
        "sqlite blobs", "cache invalidation", "cpu fallback", "onnx export", "privacy layer",
        "offline mode", "autosave safety", "session restore", "flareon switch", "burst history",
        "memory pressure", "startup speed", "api contract", "frontend state", "backend route",
        "test coverage", "golden cases", "user vocabulary", "domain words", "aggressive mode",
        "moderate listing", "longer paragraph", "class notes", "meeting notes", "research notes",
    ],
    "compound_terms": [
        ["ablation", "study"], ["semantic", "search"], ["semantic", "chunking"],
        ["paper", "structure"], ["method", "section"], ["dataset", "bias"],
        ["literature", "review"], ["citation", "mapping"], ["annotation", "quality"],
        ["boundary", "quality"], ["model", "comparison"], ["review", "comments"],
        ["query", "drift"], ["embedding", "cache"], ["evidence", "chain"],
        ["false", "positives"], ["raw", "note"], ["vector", "storage"],
        ["burst", "indexing"], ["formatting", "latency"], ["reader", "trust"],
        ["user", "profile"], ["protected", "terms"], ["short", "tokens"],
    ],
    "break_starters": [
        "also", "another", "anyway", "besides", "but", "finally", "first", "however",
        "meanwhile", "moreover", "next", "second", "so", "still", "then", "therefore",
        "third", "though", "yet",
    ],
    "soft_break_starters": ["maybe", "perhaps", "probably", "possibly"],
}


@dataclass(frozen=True)
class StabilisationProfile:
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def preferences(self) -> dict[str, str]:
        prefs = self.raw.get("formatting_preferences", {})
        return prefs if isinstance(prefs, dict) else {}

    @property
    def paragraph_density(self) -> str:
        return self.preferences.get("paragraph_density", "balanced")

    @property
    def line_break_aggressiveness(self) -> str:
        return self.preferences.get("line_break_aggressiveness", "balanced")

    @property
    def listing_aggressiveness(self) -> str:
        return self.preferences.get("listing_aggressiveness", "moderate")

    @property
    def heading_aggressiveness(self) -> str:
        return self.preferences.get("heading_aggressiveness", "conservative")

    def words(self, key: str) -> frozenset[str]:
        values = self.raw.get(key, [])
        if not isinstance(values, list):
            return frozenset()
        return frozenset(str(item).strip().lower() for item in values if str(item).strip())

    def phrases(self, key: str) -> list[str]:
        values = self.raw.get(key, [])
        if not isinstance(values, list):
            return []
        phrases = [str(item).strip().lower() for item in values if str(item).strip()]
        return sorted(set(phrases), key=lambda item: (-len(item.split()), item))

    def compound_pairs(self) -> frozenset[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        values = self.raw.get("compound_terms", [])
        if isinstance(values, list):
            for item in values:
                if isinstance(item, list) and len(item) == 2:
                    pairs.add((str(item[0]).lower(), str(item[1]).lower()))
                elif isinstance(item, str):
                    parts = item.lower().split()
                    if len(parts) == 2:
                        pairs.add((parts[0], parts[1]))
        return frozenset(pairs)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        elif isinstance(value, list) and isinstance(merged.get(key), list):
            seen: set[str] = set()
            combined: list[Any] = []
            for item in [*merged[key], *value]:
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if marker not in seen:
                    seen.add(marker)
                    combined.append(item)
            merged[key] = combined
        else:
            merged[key] = value
    return merged


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def load_stabilisation_profile() -> StabilisationProfile:
    payload = dict(BUILTIN_PROFILE)
    payload = _deep_merge(payload, _load_json(MODULE_DEFAULT_PROFILE))

    env_path = os.getenv("NOTESFLARE_STABILISATION_PROFILE")
    user_path = Path(env_path).expanduser() if env_path else STORAGE_PROFILE
    payload = _deep_merge(payload, _load_json(user_path))
    return StabilisationProfile(payload)


def reset_profile_cache() -> None:
    load_stabilisation_profile.cache_clear()
