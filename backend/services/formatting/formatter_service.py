# services/formatting/formatter_service.py

"""
Rule-driven structural formatter for NotesFlare V1.2.

This formatter is:
- Rule-based (no LLM, no generative model)
- Structural only (paragraph breaks, internal line breaks, lists, headings, quotes)
- Non-destructive toward protected product/system tokens
- Operation-emitting (returns operations, not rewritten text)

The important V1.2 upgrade here is the structure-stabilization pass: NotesFlare
users often type one continuous thought paragraph. The formatter cannot feel
"intelligent" if it only formats already-existing newlines, so this module can
propose line breaks *inside* a raw line while preserving every original word.
"""

from __future__ import annotations

import re

try:
    from services.formatting.parser_service import PROTECTED_TOKENS
except Exception:  # pragma: no cover - defensive fallback for unusual import paths
    PROTECTED_TOKENS = frozenset({
        "NotesFlare", "MetaMorph", "MiniLM", "Burst", "Flareon",
        "spaCy", "ONNX", "FastAPI", "SQLite",
    })


# Minimum token count before a line qualifies for heading detection
HEADING_MAX_TOKENS = 7

# Similarity threshold below which a paragraph break is suggested
TOPIC_BREAK_THRESHOLD = 0.45

# Internal line splitting should be helpful, not noisy. Below this, leave the
# user's sentence alone unless a very explicit boundary marker exists.
MIN_STRUCTURE_WORDS = 10

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’._-]*")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘(\[]?[A-Za-z0-9])")
_SPACE_RE = re.compile(r"[ \t]+")

# Markers that usually begin a new thought unit in raw, unpunctuated notes.
# These are deliberately small and structural; they do not rewrite content.
DISCOURSE_BREAK_STARTERS = frozenset({
    "also", "another", "anyway", "besides", "but", "finally", "first",
    "however", "meanwhile", "moreover", "next", "second", "so", "still",
    "then", "therefore", "third", "though", "yet",
})

SOFT_BREAK_STARTERS = frozenset({
    "maybe", "perhaps", "probably", "possibly",
})

# A conservative verb list for detecting a second independent clause inside
# lowercase notes without punctuation. We keep this limited to avoid over-splits.
CLAUSE_VERBS = frozenset({
    "am", "is", "are", "was", "were", "be", "been", "being",
    "become", "becomes", "became", "carry", "carries", "discuss", "discusses",
    "has", "have", "had", "make", "makes", "need", "needs", "shift", "shifts",
    "happen", "happens", "work", "works", "cost", "costs",
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


Operation = dict[str, str | int]


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
        "operation": str,
        "raw_before": str,
        "formatted_after": str,
    }
    """
    operations: list[dict] = []

    for i, signal in enumerate(line_signals):
        line = signal["text"]

        # Skip empty lines
        if not signal["token_count"]:
            continue

        # Never touch tiny protected-token-only lines such as "NotesFlare".
        if signal.get("contains_protected_token") and signal["token_count"] <= 2:
            continue

        # ── List item formatting ──────────────────────────────────────────────
        # List normalization is structural and does not change the words.
        if signal["is_list_item_candidate"]:
            formatted = _format_list_item(line)
            if formatted != line:
                operations.append(_op(i, "format_as_list_item", line, formatted))
            continue

        # ── Heading formatting ────────────────────────────────────────────────
        # Preserve protected tokens exactly (NotesFlare must not become Notesflare).
        if signal["is_heading_candidate"] and signal["token_count"] <= HEADING_MAX_TOKENS:
            formatted = _format_heading(line)
            if formatted != line:
                operations.append(_op(i, "format_as_heading", line, formatted))
            continue

        # ── Quote formatting ──────────────────────────────────────────────────
        if signal["is_quote_candidate"]:
            formatted = _format_quote(line)
            if formatted != line:
                operations.append(_op(i, "format_as_quote", line, formatted))
            continue

        # ── Internal structure stabilization ──────────────────────────────────
        # This is what makes long, raw thought dumps become readable. It can split
        # a single raw line into sentence/thought units without altering words.
        structured = _format_semantic_structure(line)
        needs_topic_prefix = _should_prefix_topic_break(i, signal, line, line_signals, similarity_scores)
        if structured != line:
            if needs_topic_prefix and not structured.startswith("\n"):
                structured = "\n" + structured
            operations.append(_op(i, "insert_line_break", line, structured))
            continue

        # ── Paragraph break insertion between existing lines ──────────────────
        if needs_topic_prefix:
            operations.append(_op(i, "insert_paragraph_break", line, "\n" + line))

    return operations


def _op(line_index: int, operation: str, raw_before: str, formatted_after: str) -> dict:
    return {
        "line_index": line_index,
        "operation": operation,
        "raw_before": raw_before,
        "formatted_after": formatted_after,
    }


def _format_list_item(line: str) -> str:
    """Normalize list item: ensure bullet is "- " prefix where applicable."""
    stripped = line.strip()
    if stripped.startswith("- "):
        return stripped
    if re.match(r"^[*•]\s", stripped):
        return "- " + stripped[2:]
    if re.match(r"^\d+[.)]\s", stripped):
        return stripped
    return line


def _format_heading(line: str) -> str:
    """Title-case a heading candidate while preserving protected tokens exactly."""
    stripped = line.strip()
    titled = stripped.title()
    return _restore_protected_tokens(stripped, titled)


def _restore_protected_tokens(original: str, formatted: str) -> str:
    """Restore exact protected token casing after safe structural formatting."""
    restored = formatted
    for token in sorted(PROTECTED_TOKENS, key=len, reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(token)}(?!\w)", re.IGNORECASE)
        # Only restore if the token was present in the original line.
        if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", original):
            restored = pattern.sub(token, restored)
    return restored


def _format_quote(line: str) -> str:
    """Ensure a straight double-quoted line uses typographic quote chars."""
    stripped = line.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        return "\u201c" + stripped[1:-1] + "\u201d"
    return stripped


def _format_semantic_structure(line: str) -> str:
    """
    Propose internal line breaks for a raw thought line.

    The method is deterministic and conservative:
    1. Sentence punctuation becomes sentence-level line breaks for long dumps.
    2. Unpunctuated notes are split on explicit discourse markers.
    3. A second independent clause can be split when a new subject+verb pattern
       appears far enough into the line.
    """
    stripped = line.strip()
    if not stripped:
        return line

    leading = line[: len(line) - len(line.lstrip())]
    trailing = line[len(line.rstrip()):]

    # Normalize repeated horizontal spaces only in the proposal. This is a
    # structural readability change; raw storage remains untouched.
    compact = _SPACE_RE.sub(" ", stripped)
    sentence_units = _split_sentences(compact)

    if len(sentence_units) >= 2:
        structured = _join_sentence_units(sentence_units)
        return f"{leading}{structured}{trailing}"

    words = _word_spans(compact)
    break_positions = _find_unpunctuated_break_positions(compact, words)
    if len(words) < MIN_STRUCTURE_WORDS and not break_positions:
        return f"{leading}{compact}{trailing}" if compact != stripped else line

    if not break_positions:
        return f"{leading}{compact}{trailing}" if compact != stripped else line

    structured = _apply_break_positions(compact, break_positions)
    return f"{leading}{structured}{trailing}"


def _split_sentences(text: str) -> list[str]:
    """Split on punctuation boundaries while preserving punctuation."""
    parts = [p.strip() for p in _SENTENCE_BOUNDARY_RE.split(text) if p.strip()]
    # Avoid turning a normal two-sentence line into a choppy note unless it is long
    # or there is a visible topic/subject transition.
    if len(parts) == 2 and len(_WORD_RE.findall(text)) < 28:
        second_first = _first_word(parts[1])
        if second_first not in TOPIC_SHIFT_STARTERS:
            return [text]
    return parts


def _join_sentence_units(sentences: list[str]) -> str:
    """
    Join sentence units into readable thought blocks.

    Related short sentences stay adjacent; larger transitions get a blank line.
    This keeps formatted notes calm instead of turning every sentence into a
    separate paragraph.
    """
    if len(sentences) <= 1:
        return sentences[0] if sentences else ""

    lines: list[str] = []
    current_block: list[str] = []

    for idx, sentence in enumerate(sentences):
        first = _first_word(sentence)
        starts_shift = first in TOPIC_SHIFT_STARTERS or _starts_named_concept(sentence)

        if idx > 0 and (starts_shift or _should_start_new_sentence_block(current_block, sentence)):
            if current_block:
                lines.append("\n".join(current_block))
                current_block = []
        current_block.append(sentence)

    if current_block:
        lines.append("\n".join(current_block))

    return "\n\n".join(lines)


def _should_start_new_sentence_block(current_block: list[str], next_sentence: str) -> bool:
    if not current_block:
        return False
    current_words = sum(len(_WORD_RE.findall(s)) for s in current_block)
    next_words = len(_WORD_RE.findall(next_sentence))

    # After two or three sentences, create breathing room in long captured text.
    if len(current_block) >= 3:
        return True

    # If the current block is already dense, move the next thought down.
    if current_words >= 42:
        return True

    # Very short definitional sentence followed by a longer explanation often
    # reads better as a separate unit.
    if current_words <= 8 and next_words >= 12:
        return True

    return False


def _find_unpunctuated_break_positions(text: str, words: list[tuple[str, int, int]]) -> list[int]:
    breaks: list[int] = []
    lowered = [w[0].lower() for w in words]

    for i, word in enumerate(lowered):
        if i < 3:
            continue

        previous_word = lowered[i - 1]
        next_word = lowered[i + 1] if i + 1 < len(lowered) else ""

        # Explicit discourse marker: "paper discusses retrieval another point..."
        if word in DISCOURSE_BREAK_STARTERS or word in SOFT_BREAK_STARTERS:
            # Explicit thought markers are allowed earlier than semantic clause
            # boundaries: "need vector db maybe sqlite..." should split after
            # only three words because "maybe" signals a new option.
            if i >= 3 and _enough_words_since_last_break(i, words, breaks, min_words=3):
                breaks.append(words[i][1])
            continue

        # Multi-word markers: "on the other hand", "in contrast".
        phrase3 = " ".join(lowered[i:i + 3])
        phrase2 = " ".join(lowered[i:i + 2])
        if phrase3 == "on the other" or phrase2 in {"in contrast", "as a"}:
            if _enough_words_since_last_break(i, words, breaks):
                breaks.append(words[i][1])
            continue

        # New subject + finite verb after a completed clause. This catches:
        # "... structure itself carries meaning embeddings become more coherent"
        # without splitting subordinate clauses like "because structure carries".
        if (
            next_word in CLAUSE_VERBS
            and _has_previous_clause(lowered[:i])
            and previous_word not in SUBORDINATORS
            and word not in SUBORDINATORS
            and word not in PRONOUN_SUBJECTS
            and _enough_words_since_last_break(i, words, breaks)
        ):
            breaks.append(words[i][1])

    return _dedupe_close_breaks(breaks)


def _word_spans(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _has_previous_clause(words: list[str]) -> bool:
    # A previous clause needs a plausible verb-like anchor before we insert a new
    # subject boundary. This prevents arbitrary noun-noun splits.
    return any(w in CLAUSE_VERBS or w.endswith(("ing", "ed")) for w in words)


def _enough_words_since_last_break(
    word_index: int,
    words: list[tuple[str, int, int]],
    breaks: list[int],
    min_words: int = 4,
) -> bool:
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
    similarity_scores: list[float] | None,
) -> bool:
    if i <= 0:
        return False

    # Do not add extra blank space after an actual blank line.
    if line_signals[i - 1].get("token_count", 0) == 0:
        return False

    previous_non_empty = _previous_non_empty_signal(i, line_signals)
    if not previous_non_empty:
        return False

    if similarity_scores and i - 1 < len(similarity_scores):
        if similarity_scores[i - 1] < TOPIC_BREAK_THRESHOLD:
            return True

    first = _first_word(line)
    if first in TOPIC_SHIFT_STARTERS:
        return True

    if signal.get("has_conjunction_start"):
        return previous_non_empty.get("token_count", 0) > 12

    return False


def _previous_non_empty_signal(i: int, line_signals: list[dict]) -> dict | None:
    for j in range(i - 1, -1, -1):
        if line_signals[j].get("token_count", 0) > 0:
            return line_signals[j]
    return None


def _first_word(text: str) -> str:
    match = _WORD_RE.search(text.strip())
    return match.group(0).lower() if match else ""


def _starts_named_concept(sentence: str) -> bool:
    stripped = sentence.strip()
    if not stripped:
        return False
    first_word = _WORD_RE.search(stripped)
    if not first_word:
        return False
    token = first_word.group(0)
    # Uppercase concepts/Product names after a previous sentence usually mean a
    # new object of attention, not just continuation.
    return token[:1].isupper() and token not in {"I", "The", "A", "An", "This", "That", "It"}
