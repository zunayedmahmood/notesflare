# services/formatting/formatter_service.py

"""
Deterministic structure stabiliser for NotesFlare V1.2.

This service proposes structural operations only. It does not rewrite the user's
words, correct grammar, change spelling, or title-case text. The raw Burst stays
sacred; this module emits reviewable operations for the diff pipeline.

2026-06 dynamic stabilisation update:
- profile-backed user/domain vocabulary
- continuous one-line list detection, e.g. "need raw note fidelity query drift and chunking"
- preference-aware line-break/listing aggressiveness
- short-token and protected-term awareness
"""

from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from services.formatting.parser_service import PROTECTED_TOKENS
except Exception:  # pragma: no cover
    PROTECTED_TOKENS = frozenset({
        "NotesFlare", "MetaMorph", "MiniLM", "Burst", "Flareon",
        "spaCy", "ONNX", "FastAPI", "SQLite",
    })

try:
    from services.formatting.stabilisation_profile_service import (
        StabilisationProfile,
        load_stabilisation_profile,
    )
except Exception:  # pragma: no cover
    StabilisationProfile = object  # type: ignore
    load_stabilisation_profile = lambda: None  # type: ignore


TOPIC_BREAK_THRESHOLD = 0.38
MIN_STRUCTURE_WORDS = 10

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’._-]*")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘(\[]?[A-Za-z0-9])")
_SPACE_RE = re.compile(r"[ \t]+")
_EXPLICIT_LIST_RE = re.compile(r"^\s*([-*•])\s+|^\s*\d+[.)]\s+")

DISCOURSE_BREAK_STARTERS = frozenset({
    "also", "another", "anyway", "besides", "but", "finally", "first",
    "however", "meanwhile", "moreover", "next", "second", "so", "still",
    "then", "therefore", "third", "though", "yet",
})
SOFT_BREAK_STARTERS = frozenset({"maybe", "perhaps", "probably", "possibly"})
CLAUSE_VERBS = frozenset({
    "am", "is", "are", "was", "were", "be", "been", "being", "become",
    "becomes", "became", "carry", "carries", "depend", "depends", "discuss",
    "discusses", "explain", "explains", "feel", "feels", "has", "have", "had",
    "improve", "improves", "make", "makes", "need", "needs", "reveal", "reveals",
    "shift", "shifts", "happen", "happens", "work", "works", "cost", "costs",
    "support", "supports", "weaken", "weakens", "stabilize", "stabilizes",
    "confuse", "confuses", "break", "breaks", "change", "changes",
})
SUBORDINATORS = frozenset({
    "because", "that", "which", "who", "when", "while", "where", "if", "although",
    "since", "after", "before", "until", "unless",
})
PRONOUN_SUBJECTS = frozenset({
    "i", "you", "he", "she", "it", "we", "they", "this", "that", "these", "those",
    "itself", "myself", "yourself", "himself", "herself", "ourselves", "themselves",
})
TOPIC_SHIFT_STARTERS = frozenset({
    "another", "however", "meanwhile", "moreover", "therefore", "next", "second",
    "third", "finally", "but", "also",
})
LIST_HEADER_WORDS = frozenset({
    "need", "needs", "todo", "todos", "tasks", "ideas", "points", "questions",
    "issues", "problems", "steps", "features", "include", "includes", "requirements",
    "check", "checks", "remember", "focus", "plan", "plans", "try", "tries", "fix",
    "fixes", "add", "adds", "compare", "review",
})
HEADING_HINT_ENDINGS = (
    "thoughts", "notes", "plan", "architecture", "design", "roadmap", "summary",
    "questions", "problems", "issues", "idea", "ideas", "review", "lesson", "class",
)
QUOTE_PATTERNS = (
    re.compile(r"^\s*quote\s+(from|:)\b", re.IGNORECASE),
    re.compile(r"^\s*(my\s+)?(supervisor|teacher|professor|client|manager)\s+said\b", re.IGNORECASE),
    re.compile(r"^\s*(said|according\s+to|as\s+said|quoted)\b", re.IGNORECASE),
)

Operation = dict[str, str | int]


@dataclass(frozen=True)
class LineContext:
    in_implicit_list: bool
    follows_heading: bool
    follows_blank: bool
    previous_non_empty_index: int | None


def generate_operations(
    line_signals: list[dict],
    similarity_scores: list[float] | None = None,
    profile: StabilisationProfile | None = None,
) -> list[dict]:
    """Return deterministic, reviewable formatting operations."""
    profile = profile or load_stabilisation_profile()
    operations: list[dict] = []
    contexts = _build_contexts(line_signals, profile)

    for i, signal in enumerate(line_signals):
        line = signal["text"]
        context = contexts[i]

        if not signal.get("token_count"):
            continue
        if signal.get("contains_protected_token") and signal.get("token_count", 0) <= 2:
            continue
        if _is_short_token_only(line, profile):
            continue

        if signal.get("is_list_item_candidate"):
            formatted = _format_explicit_list_item(line)
            if formatted != line:
                operations.append(_op(i, "format_as_list_item", line, formatted))
            continue

        if context.in_implicit_list:
            formatted = _format_implicit_list_item(line)
            if formatted != line:
                operations.append(_op(i, "format_as_list_item", line, formatted))
            continue

        if _should_format_as_heading(i, signal, line, line_signals, contexts, profile):
            formatted = _format_heading(line)
            if formatted != line:
                operations.append(_op(i, "format_as_heading", line, formatted))
            continue

        if signal.get("is_quote_candidate") or _is_quote_like(line):
            formatted = _format_quote(line)
            if formatted != line:
                operations.append(_op(i, "format_as_quote", line, formatted))
            continue

        structured = _format_semantic_structure(line, profile)
        needs_topic_prefix = _should_prefix_topic_break(i, signal, line, line_signals, contexts, similarity_scores, profile)
        if structured != line:
            if needs_topic_prefix and not structured.startswith("\n"):
                structured = "\n" + structured
            operations.append(_op(i, "insert_line_break", line, structured))
            continue

        if needs_topic_prefix:
            operations.append(_op(i, "insert_paragraph_break", line, "\n" + line))

    return operations


def _op(line_index: int, operation: str, raw_before: str, formatted_after: str) -> dict:
    return {"line_index": line_index, "operation": operation, "raw_before": raw_before, "formatted_after": formatted_after}


def _build_contexts(line_signals: list[dict], profile: StabilisationProfile) -> list[LineContext]:
    contexts: list[LineContext] = []
    active_list_header_index: int | None = None
    previous_non_empty_index: int | None = None
    previous_was_headingish = False

    for i, signal in enumerate(line_signals):
        text = signal.get("text", "")
        stripped = text.strip()
        follows_blank = i > 0 and line_signals[i - 1].get("token_count", 0) == 0

        if not stripped:
            contexts.append(LineContext(False, False, follows_blank, previous_non_empty_index))
            active_list_header_index = None
            previous_was_headingish = False
            continue

        if _is_list_header(stripped, profile):
            contexts.append(LineContext(False, previous_was_headingish, follows_blank, previous_non_empty_index))
            active_list_header_index = i
            previous_non_empty_index = i
            previous_was_headingish = False
            continue

        in_implicit_list = False
        if active_list_header_index is not None:
            in_implicit_list = _can_be_implicit_list_item(stripped, profile)
            if not in_implicit_list:
                active_list_header_index = None

        contexts.append(LineContext(in_implicit_list, previous_was_headingish, follows_blank, previous_non_empty_index))
        previous_was_headingish = _is_headingish_without_formatting(signal, stripped) and not in_implicit_list
        previous_non_empty_index = i

    return contexts


def _profile_words(profile: StabilisationProfile, key: str, fallback: frozenset[str]) -> frozenset[str]:
    try:
        values = profile.words(key)
        return values or fallback
    except Exception:
        return fallback


def _is_list_header(stripped: str, profile: StabilisationProfile) -> bool:
    if not stripped.endswith(":"):
        return False
    words = [_clean_word(w) for w in _WORD_RE.findall(stripped[:-1])]
    if not words:
        return False
    list_headers = _profile_words(profile, "list_header_words", LIST_HEADER_WORDS)
    if len(words) <= 3 and words[0] in list_headers:
        return True
    return len(words) <= 2 and _listing_aggressiveness(profile) != "conservative"


def _can_be_implicit_list_item(stripped: str, profile: StabilisationProfile) -> bool:
    if not stripped or stripped.endswith((".", "?", "!")):
        return False
    if _is_list_header(stripped, profile) or _is_quote_like(stripped):
        return False
    words = _WORD_RE.findall(stripped)
    max_words = 7 if _listing_aggressiveness(profile) == "conservative" else 11
    return 1 <= len(words) <= max_words


def _format_explicit_list_item(line: str) -> str:
    leading = line[: len(line) - len(line.lstrip())]
    stripped = line.strip()
    if stripped.startswith("- "):
        return leading + stripped
    bullet = re.match(r"^[*•]\s+(.*)$", stripped)
    if bullet:
        return leading + "- " + bullet.group(1)
    numbered = re.match(r"^\d+[.)]\s+", stripped)
    if numbered:
        return leading + stripped
    return line


def _format_implicit_list_item(line: str) -> str:
    leading = line[: len(line) - len(line.lstrip())]
    stripped = line.strip()
    if stripped.startswith("- "):
        return leading + stripped
    return f"{leading}- {stripped}"


def _should_format_as_heading(
    i: int,
    signal: dict,
    line: str,
    line_signals: list[dict],
    contexts: list[LineContext],
    profile: StabilisationProfile,
) -> bool:
    stripped = line.strip()
    if not _is_headingish_without_formatting(signal, stripped):
        return False
    if _is_short_token_only(stripped, profile):
        return False

    context = contexts[i]
    if context.in_implicit_list:
        return False
    if context.previous_non_empty_index is not None:
        prev_text = line_signals[context.previous_non_empty_index].get("text", "").strip()
        if _is_list_header(prev_text, profile):
            return False

    next_non_empty = _next_non_empty_signal(i, line_signals)
    follows_blank_or_start = i == 0 or context.follows_blank
    followed_by_content = bool(next_non_empty and next_non_empty.get("token_count", 0) >= 6)
    first = _first_word(stripped)
    has_heading_hint = first in {"chapter", "lesson", "section", "topic"} or stripped.lower().endswith(HEADING_HINT_ENDINGS)

    if profile and getattr(profile, "heading_aggressiveness", "conservative") == "aggressive":
        return (follows_blank_or_start or followed_by_content) and signal.get("token_count", 0) <= 6
    return has_heading_hint and (follows_blank_or_start or followed_by_content)


def _is_headingish_without_formatting(signal: dict, stripped: str) -> bool:
    if not signal.get("is_heading_candidate"):
        return False
    if stripped.startswith(("#", ">", "- ")) or _EXPLICIT_LIST_RE.match(stripped):
        return False
    return True


def _format_heading(line: str) -> str:
    leading = line[: len(line) - len(line.lstrip())]
    stripped = line.strip()
    if stripped.startswith("## "):
        return leading + stripped
    return f"{leading}## {stripped}"


def _is_quote_like(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith((">", "\"", "'", "“", "‘")):
        return True
    return any(pattern.search(stripped) for pattern in QUOTE_PATTERNS)


def _format_quote(line: str) -> str:
    leading = line[: len(line) - len(line.lstrip())]
    stripped = line.strip()
    if stripped.startswith("> "):
        return leading + stripped
    return f"{leading}> {stripped}"


def _format_semantic_structure(line: str, profile: StabilisationProfile) -> str:
    stripped = line.strip()
    if not stripped:
        return line

    leading = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()):]
    compact = _SPACE_RE.sub(" ", stripped)

    if _is_list_header(compact, profile) or _EXPLICIT_LIST_RE.match(compact) or _is_quote_like(compact):
        return f"{leading}{compact}{trailing}" if compact != stripped else line

    list_structured = _format_continuous_list_structure(compact, profile)
    if list_structured != compact:
        return f"{leading}{list_structured}{trailing}"

    sentence_units = _split_sentences(compact)
    if len(sentence_units) >= 2:
        structured = _join_sentence_units(sentence_units, profile)
        return f"{leading}{structured}{trailing}"

    words = _word_spans(compact)
    break_positions = _find_unpunctuated_break_positions(compact, words, profile)
    if len(words) < _min_structure_words(profile) and not break_positions:
        return f"{leading}{compact}{trailing}" if compact != stripped else line
    if not break_positions:
        return f"{leading}{compact}{trailing}" if compact != stripped else line
    structured = _apply_break_positions(compact, break_positions)
    return f"{leading}{structured}{trailing}"


def _format_continuous_list_structure(text: str, profile: StabilisationProfile) -> str:
    """Convert compact list streams into header + bullets when confidence is high."""
    tokens = _word_spans(text)
    if len(tokens) < 4:
        return text
    first = _clean_word(tokens[0][0])
    headers = _profile_words(profile, "continuous_list_headers", LIST_HEADER_WORDS)
    if first not in headers:
        return text
    if _listing_aggressiveness(profile) == "conservative" and len(tokens) < 6:
        return text

    remainder = text[tokens[0][2]:].strip(" ,;:-")
    items = _extract_continuous_list_items(remainder, profile)
    min_items = 2 if _listing_aggressiveness(profile) == "aggressive" else 3
    if len(items) < min_items:
        return text
    header = text[: tokens[0][2]].strip()
    return f"{header}:\n" + "\n".join(f"- {item}" for item in items)


def _extract_continuous_list_items(remainder: str, profile: StabilisationProfile) -> list[str]:
    phrases = profile.phrases("continuous_list_item_phrases") if profile else []
    if not phrases:
        return []
    lowered = remainder.lower()
    matches: list[tuple[int, int, str]] = []
    occupied: list[tuple[int, int]] = []

    for phrase in phrases:
        pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)
        for match in pattern.finditer(remainder):
            start, end = match.span()
            if any(not (end <= a or start >= b) for a, b in occupied):
                continue
            occupied.append((start, end))
            matches.append((start, end, remainder[start:end].strip()))

    if len(matches) < 2:
        return []
    matches.sort(key=lambda item: item[0])

    items: list[str] = []
    last_end = 0
    connectors = {"and", "or", "plus", "then"}

    for start, end, phrase_text in matches:
        gap = remainder[last_end:start].strip(" ,;:-")
        if gap:
            raw_gap_words = [w for w in _WORD_RE.findall(gap)]
            gap_words = [_clean_word(w) for w in raw_gap_words if _clean_word(w) not in connectors]
            gap_clean = " ".join(gap_words)
            if gap_clean and gap_clean not in connectors:
                if len(gap_words) <= 3:
                    # Preserve short/raw user tokens instead of silently dropping
                    # them from a continuous-list conversion. Connector words like
                    # "and/plus/then" are structural glue and are not rendered as
                    # standalone list items. If a gap contains multiple short
                    # tokens, keep each token as a separate item.
                    gap_items = [word for word in raw_gap_words if _clean_word(word) not in connectors]
                    if _all_short_gap_tokens(gap_items, profile):
                        items.extend(gap_items)
                    else:
                        items.append(" ".join(gap_items))
                else:
                    return []
        items.append(phrase_text)
        last_end = end

    trailing = remainder[last_end:].strip(" ,;:-")
    if trailing:
        raw_trailing_words = [w for w in _WORD_RE.findall(trailing)]
        trailing_words = [_clean_word(w) for w in raw_trailing_words if _clean_word(w) not in connectors]
        trailing_clean = " ".join(trailing_words)
        if trailing_clean and trailing_clean not in connectors:
            if len(trailing_words) <= 3:
                trailing_items = [word for word in raw_trailing_words if _clean_word(word) not in connectors]
                if _all_short_gap_tokens(trailing_items, profile):
                    items.extend(trailing_items)
                else:
                    items.append(" ".join(trailing_items))
            else:
                return []

    # Remove accidental duplicate nearby items while preserving order.
    deduped: list[str] = []
    for item in items:
        normalized = " ".join(_clean_word(w) for w in _WORD_RE.findall(item))
        if normalized and normalized not in {"and", "or", "plus", "then"}:
            if not deduped or normalized != " ".join(_clean_word(w) for w in _WORD_RE.findall(deduped[-1])):
                deduped.append(item)
    return deduped


def _all_short_gap_tokens(items: list[str], profile: StabilisationProfile) -> bool:
    if not items:
        return False
    short_tokens = _profile_words(profile, "short_tokens", frozenset())
    return all(_clean_word(item) in short_tokens or len(_clean_word(item)) <= 2 for item in items)


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_BOUNDARY_RE.split(text) if p.strip()]
    if len(parts) == 2 and len(_WORD_RE.findall(text)) < 28:
        second_first = _first_word(parts[1])
        if second_first not in TOPIC_SHIFT_STARTERS:
            return [text]
    return parts


def _join_sentence_units(sentences: list[str], profile: StabilisationProfile) -> str:
    if len(sentences) <= 1:
        return sentences[0] if sentences else ""
    lines: list[str] = []
    current_block: list[str] = []
    for idx, sentence in enumerate(sentences):
        first = _first_word(sentence)
        starts_shift = first in TOPIC_SHIFT_STARTERS or _starts_named_concept(sentence)
        if idx > 0 and (starts_shift or _should_start_new_sentence_block(current_block, sentence, profile)):
            if current_block:
                lines.append("\n".join(current_block))
                current_block = []
        current_block.append(sentence)
    if current_block:
        lines.append("\n".join(current_block))
    return "\n\n".join(lines)


def _should_start_new_sentence_block(current_block: list[str], next_sentence: str, profile: StabilisationProfile) -> bool:
    if not current_block:
        return False
    current_words = sum(len(_WORD_RE.findall(s)) for s in current_block)
    next_words = len(_WORD_RE.findall(next_sentence))
    density = getattr(profile, "paragraph_density", "balanced") if profile else "balanced"
    max_sentences = 4 if density == "longer" else 2 if density == "shorter" else 3
    dense_word_limit = 60 if density == "longer" else 30 if density == "shorter" else 42
    if len(current_block) >= max_sentences:
        return True
    if current_words >= dense_word_limit:
        return True
    if current_words <= 8 and next_words >= 12 and density != "longer":
        return True
    return False


def _find_unpunctuated_break_positions(text: str, words: list[tuple[str, int, int]], profile: StabilisationProfile) -> list[int]:
    breaks: list[int] = []
    lowered = [_clean_word(w[0]) for w in words]
    hard_starters = _profile_words(profile, "break_starters", DISCOURSE_BREAK_STARTERS)
    soft_starters = _profile_words(profile, "soft_break_starters", SOFT_BREAK_STARTERS)
    min_first = 2 if _line_break_aggressiveness(profile) == "aggressive" else 4

    for i, word in enumerate(lowered):
        if i < 3:
            continue
        previous_word = lowered[i - 1]
        next_word = lowered[i + 1] if i + 1 < len(lowered) else ""

        if word in hard_starters or word in soft_starters:
            if i >= 3 and _enough_words_since_last_break(i, words, breaks, min_words=3):
                breaks.append(words[i][1])
            continue

        phrase3 = " ".join(lowered[i:i + 3])
        phrase2 = " ".join(lowered[i:i + 2])
        if phrase3 == "on the other" or phrase2 in {"in contrast", "as a"}:
            if _enough_words_since_last_break(i, words, breaks):
                breaks.append(words[i][1])
            continue

        if (
            next_word in CLAUSE_VERBS
            and _has_previous_clause(lowered[:i])
            and previous_word not in SUBORDINATORS
            and word not in SUBORDINATORS
            and word not in PRONOUN_SUBJECTS
            and _looks_like_new_clause_subject(word)
            and not _looks_like_compound_term(previous_word, word, profile)
            and _enough_words_since_last_break(i, words, breaks, min_words=min_first)
        ):
            breaks.append(words[i][1])

    return _dedupe_close_breaks(breaks)


def _looks_like_new_clause_subject(word: str) -> bool:
    if word.endswith("s") and len(word) > 3:
        return True
    return word in {"embedding", "embeddings", "latency", "retrieval", "formatting", "chunking", "storage", "pipeline", "structure", "model", "system"}


def _looks_like_compound_term(previous_word: str, word: str, profile: StabilisationProfile) -> bool:
    fallback = {
        ("ablation", "study"), ("semantic", "search"), ("paper", "structure"),
        ("method", "section"), ("dataset", "bias"), ("literature", "review"),
        ("citation", "mapping"), ("annotation", "quality"), ("boundary", "quality"),
        ("model", "comparison"), ("review", "comments"), ("query", "drift"),
        ("embedding", "cache"), ("evidence", "chain"), ("false", "positives"),
        ("raw", "note"), ("vector", "storage"), ("formatting", "latency"),
    }
    try:
        pairs = profile.compound_pairs()
        return (previous_word, word) in (pairs or fallback)
    except Exception:
        return (previous_word, word) in fallback


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _has_previous_clause(words: list[str]) -> bool:
    return any(w in CLAUSE_VERBS or w.endswith(("ing", "ed")) for w in words)


def _enough_words_since_last_break(word_index: int, words: list[tuple[str, int, int]], breaks: list[int], min_words: int = 4) -> bool:
    if not breaks:
        return word_index >= min_words
    last_char = breaks[-1]
    words_after_last = sum(1 for _, start, _ in words[:word_index] if start > last_char)
    return words_after_last >= min_words


def _dedupe_close_breaks(breaks: list[int]) -> list[int]:
    deduped: list[int] = []
    for pos in sorted(set(breaks)):
        if not deduped or pos - deduped[-1] > 16:
            deduped.append(pos)
    return deduped


def _apply_break_positions(text: str, breaks: list[int]) -> str:
    parts: list[str] = []
    last = 0
    for pos in breaks:
        parts.append(text[last:pos].strip())
        last = pos
    parts.append(text[last:].strip())
    return "\n\n".join(part for part in parts if part)


def _should_prefix_topic_break(
    i: int,
    signal: dict,
    line: str,
    line_signals: list[dict],
    contexts: list[LineContext],
    similarity_scores: list[float] | None,
    profile: StabilisationProfile,
) -> bool:
    if i <= 0:
        return False
    context = contexts[i]
    if context.follows_blank or context.in_implicit_list:
        return False
    previous_index = context.previous_non_empty_index
    if previous_index is None:
        return False

    previous_signal = line_signals[previous_index]
    previous_text = previous_signal.get("text", "").strip()
    stripped = line.strip()
    if _is_list_header(previous_text, profile):
        return False
    if _can_be_implicit_list_item(stripped, profile) and _can_be_implicit_list_item(previous_text, profile):
        return False

    first = _first_word(stripped)
    if first in TOPIC_SHIFT_STARTERS:
        return True
    if signal.get("has_conjunction_start") and previous_signal.get("token_count", 0) > 12:
        return True

    if similarity_scores and i - 1 < len(similarity_scores):
        score = similarity_scores[i - 1]
        prev_tokens = previous_signal.get("token_count", 0)
        this_tokens = signal.get("token_count", 0)
        threshold = _topic_break_threshold(profile)
        min_tokens = 4 if _line_break_aggressiveness(profile) == "aggressive" else 6
        if score < threshold and prev_tokens >= min_tokens and this_tokens >= min_tokens:
            return True

    if previous_text.startswith("## ") or _should_format_as_heading(previous_index, previous_signal, previous_text, line_signals, contexts, profile):
        return signal.get("token_count", 0) >= 4
    return False


def _topic_break_threshold(profile: StabilisationProfile) -> float:
    mode = _line_break_aggressiveness(profile)
    if mode == "aggressive":
        return 0.48
    if mode == "conservative":
        return 0.30
    return TOPIC_BREAK_THRESHOLD


def _min_structure_words(profile: StabilisationProfile) -> int:
    mode = _line_break_aggressiveness(profile)
    if mode == "aggressive":
        return 7
    if mode == "conservative":
        return 13
    return MIN_STRUCTURE_WORDS


def _line_break_aggressiveness(profile: StabilisationProfile) -> str:
    return getattr(profile, "line_break_aggressiveness", "balanced") if profile else "balanced"


def _listing_aggressiveness(profile: StabilisationProfile) -> str:
    return getattr(profile, "listing_aggressiveness", "moderate") if profile else "moderate"


def _is_short_token_only(line: str, profile: StabilisationProfile) -> bool:
    words = [_clean_word(w) for w in _WORD_RE.findall(line)]
    if not words:
        return False
    short_tokens = _profile_words(profile, "short_tokens", frozenset())
    protected = {term.lower() for term in PROTECTED_TOKENS}
    return len(words) <= 3 and all((w in short_tokens or w in protected or len(w) <= 2) for w in words)


def _next_non_empty_signal(i: int, line_signals: list[dict]) -> dict | None:
    for j in range(i + 1, len(line_signals)):
        if line_signals[j].get("token_count", 0) > 0:
            return line_signals[j]
    return None


def _first_word(text: str) -> str:
    match = _WORD_RE.search(text.strip())
    return _clean_word(match.group(0)) if match else ""


def _clean_word(word: str) -> str:
    return word.strip("'’\".,;:!?()[]{}<> ").lower()


def _starts_named_concept(sentence: str) -> bool:
    stripped = sentence.strip()
    if not stripped:
        return False
    first_word = _WORD_RE.search(stripped)
    if not first_word:
        return False
    token = first_word.group(0)
    return token[:1].isupper() and token not in {"I", "The", "A", "An", "This", "That", "It"}
