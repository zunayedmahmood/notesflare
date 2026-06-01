#!/usr/bin/env python3
"""Generate 1,000 continuous-stream NotesFlare stabilisation cases."""
from __future__ import annotations

import json
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
OUTPUT = MODULE_DIR / "examples_1000_continuous_stream.json"

GENRES = [
    "research_stream", "developer_stream", "brainstorm_stream", "class_stream",
    "meeting_stream", "architecture_stream", "lab_stream", "personal_stream",
    "language_stream", "product_stream",
]
HEADERS = ["need", "fix", "add", "check", "review", "compare", "include", "focus", "todo", "questions"]
PHRASES = {
    "research_stream": ["raw note fidelity", "query drift", "semantic chunking", "ablation study", "evidence chain", "citation mapping", "false positives", "evaluation metric", "literature review", "method section"],
    "developer_stream": ["api contract", "backend route", "frontend state", "sqlite first", "cache invalidation", "cpu fallback", "test coverage", "golden cases", "startup speed", "onnx export"],
    "brainstorm_stream": ["pricing model", "landing page", "founder story", "user feedback", "launch plan", "feature scope", "demo script", "brand voice", "market angle", "risk list"],
    "class_stream": ["lecture summary", "formula revision", "example problem", "definition recall", "exam pattern", "chapter notes", "teacher hint", "practice sheet", "common mistake", "quick recap"],
    "meeting_stream": ["client feedback", "budget risk", "scope change", "timeline issue", "handover note", "decision log", "followup email", "meeting agenda", "approval path", "next milestone"],
    "architecture_stream": ["burst indexing", "vector storage", "embedding cache", "diff review", "session restore", "flareon switch", "line breaks", "list detection", "quote detection", "heading detection"],
    "lab_stream": ["sample id", "control group", "temperature drift", "sensor noise", "calibration step", "raw reading", "trial repeat", "observation note", "result table", "error source"],
    "personal_stream": ["sleep routine", "japanese practice", "reading habit", "workout plan", "family errand", "expense check", "call reminder", "travel idea", "food list", "weekend plan"],
    "language_stream": ["kanji review", "grammar point", "listening drill", "speaking practice", "shadowing audio", "vocab deck", "sentence pattern", "particle confusion", "mock test", "daily revision"],
    "product_stream": ["user profile", "short tokens", "protected terms", "aggressive mode", "moderate listing", "longer paragraph", "privacy layer", "offline mode", "autosave safety", "benchmark loop"],
}
SHORTS = ["np", "asap", "rn", "btw", "idk", "mvp", "api", "db", "ui", "ux"]
CONNECTORS = [" ", " and ", " plus ", " then ", " "]


def make_case(index: int) -> dict:
    genre = GENRES[index % len(GENRES)]
    header = HEADERS[index % len(HEADERS)]
    pool = PHRASES[genre]
    count = 3 + (index % 4)  # 3-6 items
    start = (index * 3) % len(pool)
    items = [pool[(start + j) % len(pool)] for j in range(count)]

    tags = ["continuous_stream", "continuous_list"]
    prefix_items: list[str] = []
    suffix = ""

    variant = index % 8
    if variant == 1:
        prefix_items = [SHORTS[index % len(SHORTS)]]
        tags.append("short_token")
    elif variant == 2:
        suffix = " maybe later"
        tags.append("option_tail")
    elif variant == 3:
        header = f"{header}"
        tags.append("plain_space")
    elif variant == 4:
        prefix_items = [SHORTS[index % len(SHORTS)], SHORTS[(index + 3) % len(SHORTS)]]
        tags.extend(["short_token", "multi_short_token"])
    elif variant == 5:
        tags.append("connector_and")
    elif variant == 6:
        tags.append("connector_plus")
    else:
        tags.append("compact")

    all_items = prefix_items + items
    text = header
    for pos, item in enumerate(all_items):
        connector = CONNECTORS[(index + pos) % len(CONNECTORS)]
        # First item should usually be separated with a plain space to mimic raw streams.
        if pos == 0:
            connector = " "
        text += connector + item
    text += suffix

    expected = f"{header}:\n" + "\n".join(f"- {item}" for item in all_items)
    if suffix.strip():
        expected += f"\n- {suffix.strip()}"

    return {
        "id": f"nf-continuous-{index + 1:04d}",
        "genre": genre,
        "tags": tags,
        "raw_text": text,
        "expected_structured_text": expected,
    }


def main() -> int:
    examples = [make_case(i) for i in range(1000)]
    payload = {
        "dataset": "NotesFlare continuous stream stabilisation cases",
        "description": "One-line raw thought streams that should often become hidden structural list proposals.",
        "count": len(examples),
        "examples": examples,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(examples)} examples to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
