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
