# services/formatting/parser_service.py

"""
NLP structural parsing using spaCy when available, with a deterministic
lightweight fallback when the optional model is missing.

Responsibilities:
- Sentence-like line boundary signals
- Structural candidates: lists, headings, quotes, discourse conjunction starts
- Protected token detection so product/system names are never altered

The V1.2 formatter must never hard-fail simply because the spaCy English model
has not been downloaded on a developer machine. If `en_core_web_sm` is present,
we use it. Otherwise we use `spacy.blank("en")` plus deterministic heuristics.
"""

from functools import lru_cache
import re
import spacy

# Protected tokens — must NEVER be altered by formatting
PROTECTED_TOKENS = frozenset([
    "NotesFlare", "MetaMorph", "MiniLM", "Burst", "Flareon",
    "spaCy", "ONNX", "FastAPI", "SQLite",
])

_LIST_RE = re.compile(r"^[-*•]\s|^\d+[.)]\s")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_VERB_HINTS = frozenset({
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "done", "have", "has", "had",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    "need", "needs", "needed", "want", "wants", "wanted", "make", "makes", "made",
    "use", "uses", "used", "build", "builds", "built", "run", "runs", "ran",
    "think", "thinks", "thought", "write", "writes", "wrote", "create", "creates", "created",
})


@lru_cache(maxsize=1)
def _load_model():
    """Load spaCy once. Prefer en_core_web_sm; fall back to a blank English model."""
    try:
        nlp = spacy.load("en_core_web_sm")
        nlp.meta["notesflare_fallback"] = False
        return nlp
    except OSError:
        nlp = spacy.blank("en")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        nlp.meta["notesflare_fallback"] = True
        return nlp


def parse_lines(lines: list[str]) -> list[dict]:
    """
    Parse a list of text lines and return structural signals per line.

    Returns a list of dicts:
    {
        "line_index": int,
        "text": str,
        "is_sentence_start": bool,
        "is_sentence_end": bool,
        "is_list_item_candidate": bool,
        "is_heading_candidate": bool,
        "is_quote_candidate": bool,
        "has_conjunction_start": bool,
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
        results.append(_extract_signals(idx, line, doc))

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
    stripped = line.strip()
    tokens = [t.text for t in doc if not t.is_space]
    token_count = len(tokens)
    first_token = tokens[0].lower() if tokens else ""

    is_list = bool(_LIST_RE.match(stripped))

    has_verb = _has_verb(doc, stripped)
    is_heading = (
        token_count <= 6
        and not has_verb
        and not stripped.endswith((".", "?", "!", ":", ";"))
        and len(stripped) > 2
        and not is_list
    )

    quote_starters = {"said", "according", "as", "quoted", "per"}
    is_quote = (
        stripped.startswith(('"', "'", "\u201c", "\u2018"))
        or first_token in quote_starters
    )

    conjunctions = {"and", "but", "or", "so", "yet", "nor", "for"}
    has_conj_start = first_token in conjunctions

    # Some spaCy pipelines expose sentence boundaries; the fallback sentencizer
    # also does. If anything unusual happens, use punctuation heuristics instead.
    try:
        sents = list(doc.sents)
        is_sent_start = bool(sents)
        is_sent_end = bool(sents) and stripped.endswith((".", "?", "!"))
    except ValueError:
        is_sent_start = bool(stripped)
        is_sent_end = stripped.endswith((".", "?", "!"))

    contains_protected = _contains_protected_token(stripped, tokens)

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


def _has_verb(doc, stripped: str) -> bool:
    """Use POS tags when available, otherwise conservative word heuristics."""
    if any(getattr(t, "pos_", "") in ("VERB", "AUX") for t in doc):
        return True

    words = [w.lower() for w in _WORD_RE.findall(stripped)]
    if any(w in _VERB_HINTS for w in words):
        return True

    # Avoid treating gerund-like short headings such as "getting started" as verbs.
    if len(words) > 3 and any(w.endswith(("ing", "ed")) for w in words):
        return True

    return False


def _contains_protected_token(stripped: str, tokens: list[str]) -> bool:
    token_set = set(tokens)
    if token_set & PROTECTED_TOKENS:
        return True
    return any(re.search(rf"(?<!\w){re.escape(token)}(?!\w)", stripped) for token in PROTECTED_TOKENS)
