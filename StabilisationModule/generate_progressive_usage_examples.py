#!/usr/bin/env python3
"""Generate progressive usage-learning benchmark cases for NotesFlare."""

from __future__ import annotations

import json
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
OUTPUT = MODULE_DIR / "examples_1000_progressive_usage.json"

GENRES = [
    "research_usage_stream", "developer_usage_stream", "class_usage_stream",
    "meeting_usage_stream", "language_usage_stream", "product_usage_stream",
    "architecture_usage_stream", "lab_usage_stream", "personal_usage_stream", "startup_usage_stream",
]
HEADERS = ["need", "fix", "add", "check", "review", "compare", "focus", "remember", "todo", "plan"]
KNOWN_PHRASES = [
    "raw note fidelity", "query drift", "chunking", "semantic search", "embedding cache",
    "api contract", "frontend state", "backend route", "test coverage", "golden cases",
    "meeting agenda", "decision log", "client feedback", "followup email", "risk list",
    "grammar point", "sentence pattern", "kanji review", "shadowing audio", "mock test",
]
SHORT_TOKENS = ["np", "asap", "rn", "api", "db", "ui", "ux", "mvp", "eta", "qa", "jwt", "sku", "pos", "cpu", "gpu", "n3", "n4", "n5"]
CUSTOM_PHRASES = [
    "mext interview", "jlpt n3", "sop draft", "visa timeline", "tokutei path",
    "coolprop run", "brayton cycle", "sco2 validation", "braibench bn", "hci mouse",
    "ola report", "daraz scrape", "pandamart branch", "unilever sku", "aogga mapping",
    "beximco boiler", "compressor note", "water treatment", "mext professor", "lab pitch",
    "madestic website", "deshio order", "errum inventory", "lazychat sync", "smartself qr",
]
REJECT_PHRASES = [
    "quick thought however tiny note should stay raw",
    "np asap next do not learn this noise",
    "rn later but still keep same line",
    "idk maybe this is not a list",
    "small reminder however user rejects break",
    "todo maybe not actual structure",
    "tiny note next accidental rejection case",
]

SIM_ACCEPT_LIST = {
    "accept_operations": ["insert_line_break", "format_as_list_item", "format_as_quote"],
    "reject_operations": ["format_as_heading"],
    "default_decision": "accept",
}
SIM_REJECT_NOISE = {
    "reject_operations": ["insert_line_break", "insert_paragraph_break", "format_as_heading", "format_as_quote"],
    "default_decision": "reject",
}


def raw_stream(header: str, items: list[str], connectors: list[str] | None = None) -> str:
    connectors = connectors or [" ", " and ", " then ", " plus "]
    text = header
    for idx, item in enumerate(items):
        text += connectors[idx % len(connectors)] + item
    return " ".join(text.split())


def make_example(index: int, phase: str, genre: str, raw_text: str, tags: list[str], simulation: dict, effect: str) -> dict:
    return {
        "id": f"nf-progress-{index:04d}",
        "genre": genre,
        "phase": phase,
        "tags": tags,
        "raw_text": raw_text,
        "simulation": simulation,
        "expected_profile_effect": effect,
    }


def main() -> None:
    examples: list[dict] = []
    idx = 1

    # Phase 1: teach generic continuous lists from already-known phrase anchors.
    for i in range(250):
        genre = GENRES[i % len(GENRES)]
        header = HEADERS[i % len(HEADERS)]
        short = SHORT_TOKENS[i % len(SHORT_TOKENS)]
        items = [KNOWN_PHRASES[i % len(KNOWN_PHRASES)], short, KNOWN_PHRASES[(i + 7) % len(KNOWN_PHRASES)]]
        raw = raw_stream(header, items)
        examples.append(make_example(
            idx, "phase_1_known_continuous_lists", genre, raw,
            ["progressive", "continuous_list", "short_token", "accept_teaches_profile"],
            SIM_ACCEPT_LIST,
            "accepted continuous-list diffs reinforce list headers, short tokens, and item phrases",
        ))
        idx += 1

    # Phase 2: insert custom user/domain phrases as gaps around known anchors.
    for i in range(250):
        genre = GENRES[(i + 3) % len(GENRES)]
        header = HEADERS[(i + 2) % len(HEADERS)]
        custom_a = CUSTOM_PHRASES[i % len(CUSTOM_PHRASES)]
        custom_b = CUSTOM_PHRASES[(i + 9) % len(CUSTOM_PHRASES)]
        known_a = KNOWN_PHRASES[(i + 4) % len(KNOWN_PHRASES)]
        known_b = KNOWN_PHRASES[(i + 11) % len(KNOWN_PHRASES)]
        short = SHORT_TOKENS[(i + 5) % len(SHORT_TOKENS)]
        raw = raw_stream(header, [custom_a, known_a, short, custom_b, known_b], [" ", " and ", " plus ", " then "])
        examples.append(make_example(
            idx, "phase_2_custom_vocabulary_discovery", genre, raw,
            ["progressive", "custom_keyword", "short_token", "accepted_only_learning"],
            SIM_ACCEPT_LIST,
            "accepted diffs should learn custom item phrases and short tokens from list gaps",
        ))
        idx += 1

    # Phase 3: use the custom phrases more directly; profile should now help.
    for i in range(250):
        genre = GENRES[(i + 6) % len(GENRES)]
        header = HEADERS[(i + 5) % len(HEADERS)]
        custom_a = CUSTOM_PHRASES[i % len(CUSTOM_PHRASES)]
        custom_b = CUSTOM_PHRASES[(i + 3) % len(CUSTOM_PHRASES)]
        custom_c = CUSTOM_PHRASES[(i + 14) % len(CUSTOM_PHRASES)]
        short_a = SHORT_TOKENS[i % len(SHORT_TOKENS)]
        short_b = SHORT_TOKENS[(i + 8) % len(SHORT_TOKENS)]
        raw = raw_stream(header, [short_a, custom_a, custom_b, short_b, custom_c], [" ", " ", " and ", " plus "])
        examples.append(make_example(
            idx, "phase_3_profile_assisted_custom_lists", genre, raw,
            ["progressive", "profile_assisted", "custom_keyword", "short_token"],
            SIM_ACCEPT_LIST,
            "later examples should format better because accepted phase-2 diffs updated the profile",
        ))
        idx += 1

    # Phase 4: mix accepted preference examples with explicit rejected noise. Rejections
    # are tracked but must not update the profile.
    for i in range(250):
        genre = GENRES[(i + 8) % len(GENRES)]
        if i % 5 == 0:
            # These are intentionally good-looking structures that the simulated
            # user rejects. The learning layer must log the rejection but must not
            # update profile evidence from it.
            header = HEADERS[(i + 4) % len(HEADERS)]
            raw = raw_stream(header, [
                KNOWN_PHRASES[(i + 1) % len(KNOWN_PHRASES)],
                SHORT_TOKENS[(i + 1) % len(SHORT_TOKENS)],
                CUSTOM_PHRASES[(i + 6) % len(CUSTOM_PHRASES)],
            ], [" ", " and ", " then "])
            examples.append(make_example(
                idx, "phase_4_rejection_audit_no_learning", genre, raw,
                ["progressive", "rejection_simulation", "must_not_learn_from_rejection", "accidental_rejection_case"],
                SIM_REJECT_NOISE,
                "rejected structural diffs are tracked but must not update profile evidence",
            ))
        else:
            header = HEADERS[(i + 1) % len(HEADERS)]
            items = [
                CUSTOM_PHRASES[(i + 2) % len(CUSTOM_PHRASES)],
                SHORT_TOKENS[(i + 2) % len(SHORT_TOKENS)],
                CUSTOM_PHRASES[(i + 15) % len(CUSTOM_PHRASES)],
                KNOWN_PHRASES[(i + 9) % len(KNOWN_PHRASES)],
            ]
            raw = raw_stream(header, items, [" ", " and ", " then ", " plus "])
            examples.append(make_example(
                idx, "phase_4_mature_profile", genre, raw,
                ["progressive", "mature_profile", "custom_keyword", "short_token"],
                SIM_ACCEPT_LIST,
                "mature profile should continue accepting good structural list diffs",
            ))
        idx += 1

    payload = {
        "dataset_id": "notesflare-progressive-usage-1000",
        "description": "Progressive accept-only usage-learning benchmark with short tokens, custom keywords, and simulated accept/reject decisions.",
        "learning_rule": "The benchmark accepts preferred structural diffs and rejects selected noise; profile updates must use accepted diffs only.",
        "count": len(examples),
        "examples": examples,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(examples)} examples to {OUTPUT}")


if __name__ == "__main__":
    main()
