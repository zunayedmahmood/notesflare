# NotesFlare V1.2 — NLP Feature Verification Guide

> **AI Instruction File: NLP Pipeline Deep Verification**
> This file is a complete verification guide for every NLP feature introduced in V1.2.
> It covers spaCy parsing correctness, MiniLM embedding behavior, chunker integrity,
> formatter rule fidelity, and the immutability guarantees of the full pipeline.
> Read `V1_2_BACKEND.md` before this file.
> Run every test in this file BEFORE declaring V1.2 NLP implementation complete.

---

## 0. WHY THIS FILE EXISTS

The V1.2 formatting pipeline introduces three non-trivial machine-learning components:

1. **spaCy (`en_core_web_sm`)** — NLP structural parsing
2. **MiniLM (`all-MiniLM-L6-v2`)** — sentence embeddings via sentence-transformers
3. **ONNX Runtime** — backend accelerator for embeddings

Each of these has its own failure modes that silent `try/except` blocks in the pipeline can mask. This file forces explicit verification of each stage in isolation before testing them together.

### The Golden Rule of This File
> **Never mark a stage as passing just because the API returned 200.**
> A 200 with `diff_count: 0` on content that should have diffs is a silent failure.
> Every stage must be tested for its *specific output shape and value range*.

---

## 1. ENVIRONMENT VERIFICATION

Run these checks before any NLP testing. If any fail, stop and fix before continuing.

### 1.1 Python environment

```bash
# From the backend/ directory

# spaCy
python -c "
import spacy
nlp = spacy.load('en_core_web_sm')
doc = nlp('The quick brown fox jumps over the lazy dog.')
print('spaCy OK')
print('  Model:', nlp.meta['name'])
print('  Pipeline:', nlp.pipe_names)
print('  Sentence count:', len(list(doc.sents)))
print('  Token count:', len(doc))
"
# Expected output:
# spaCy OK
# Model: en_core_web_sm
# Pipeline: ['tok2vec', 'tagger', 'parser', 'sents', 'ner', 'attribute_ruler', 'lemmatizer']
# Sentence count: 1
# Token count: 9 (may vary slightly with punctuation)
```

```bash
# sentence-transformers + ONNX
python -c "
from sentence_transformers import SentenceTransformer
import numpy as np
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
embeddings = model.encode(['Hello world', 'This is a test'])
print('sentence-transformers OK')
print('  Embedding shape:', embeddings.shape)
print('  Embedding dtype:', embeddings.dtype)
assert embeddings.shape == (2, 384), f'Expected (2, 384), got {embeddings.shape}'
print('  Shape assertion passed')
"
# Expected:
# sentence-transformers OK
# Embedding shape: (2, 384)
# Embedding dtype: float32
# Shape assertion passed
```

```bash
# ONNX Runtime availability
python -c "
import onnxruntime as ort
print('ONNX Runtime OK')
print('  Version:', ort.__version__)
print('  Providers:', ort.get_available_providers())
"
# Expected: at least ['CPUExecutionProvider'] in providers
```

### 1.2 Model loading performance

```bash
# Measure first-load time (cold start)
python -c "
import time

start = time.perf_counter()
import spacy
nlp = spacy.load('en_core_web_sm')
t1 = time.perf_counter()
print(f'spaCy cold load: {(t1-start)*1000:.0f}ms')

start2 = time.perf_counter()
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
t2 = time.perf_counter()
print(f'MiniLM cold load: {(t2-start2)*1000:.0f}ms')
"
# Acceptable thresholds:
# spaCy cold load: < 500ms
# MiniLM cold load: < 5000ms on first call (model download)
#                   < 2000ms on subsequent calls (cached)
```

---

## 2. LEXER SERVICE VERIFICATION

**File:** `backend/services/formatting/lexer_service.py`

### 2.1 Manual test matrix

Run each test case individually and verify the exact output:

```bash
python -c "
from services.formatting.lexer_service import normalize_text, split_into_lines

# Test 1: NFC normalization
decomposed = 'cafe\u0301'   # e + combining accent = é (decomposed form)
result = normalize_text(decomposed)
assert result == 'caf\u00e9', f'FAIL NFC: got {repr(result)}'
print('PASS: NFC normalization')

# Test 2: Windows line endings
text = 'line one\r\nline two\r\n'
result = normalize_text(text)
assert '\r' not in result, 'FAIL: CRLF not removed'
print('PASS: Windows CRLF normalization')

# Test 3: Trailing whitespace
text = 'hello   \nworld   '
result = normalize_text(text)
lines = result.split('\n')
assert lines[0] == 'hello', f'FAIL trailing: got {repr(lines[0])}'
assert lines[1] == 'world', f'FAIL trailing: got {repr(lines[1])}'
print('PASS: Trailing whitespace stripped')

# Test 4: Multiple blank lines collapsed
text = 'line one\n\n\n\n\nline two'
result = normalize_text(text)
assert '\n\n\n' not in result, 'FAIL: 3+ blank lines not collapsed'
assert '\n\n' in result, 'FAIL: double newline unexpectedly removed'
print('PASS: Consecutive blank lines collapsed to max 2')

# Test 5: Words unchanged
original = 'NotesFlare MiniLM spaCy FastAPI'
result = normalize_text(original)
assert result == original, f'FAIL: words changed: {repr(result)}'
print('PASS: Words unchanged')

# Test 6: Empty string
assert normalize_text('') == '', 'FAIL: empty string'
print('PASS: Empty string returns empty string')

print()
print('All lexer tests passed.')
"
```

```bash
python -c "
from services.formatting.lexer_service import split_into_lines

# Test: Basic split
lines = split_into_lines('hello\nworld')
assert lines == ['hello', 'world'], f'FAIL: {lines}'
print('PASS: Basic line split')

# Test: Blank lines preserved in split
lines = split_into_lines('hello\n\nworld')
assert lines == ['hello', '', 'world'], f'FAIL: {lines}'
print('PASS: Blank lines preserved in split')

# Test: Single line no newline
lines = split_into_lines('hello')
assert lines == ['hello'], f'FAIL: {lines}'
print('PASS: Single line (no newline)')

# Test: Empty string yields one empty element
lines = split_into_lines('')
assert lines == [''], f'FAIL: {lines}'
print('PASS: Empty string split')
"
```

### 2.2 Lexer immutability contract

The lexer must NEVER change any word. Verify with a word-level diff:

```bash
python -c "
from services.formatting.lexer_service import normalize_text

samples = [
    'I think this might work but need to verify',
    'NotesFlare is a persistent thought stream',
    'UPPERCASE WORDS LIKE THIS should remain',
    'numbers like 42 and 3.14 must stay',
    \"contractions like can't and won't must stay\",
]

import re

def extract_words(text):
    return set(re.findall(r\"[a-zA-Z0-9']+\", text))

for sample in samples:
    result = normalize_text(sample)
    original_words = extract_words(sample)
    result_words = extract_words(result)
    added = result_words - original_words
    removed = original_words - result_words
    assert not added and not removed, f'FAIL: added={added} removed={removed} in: {repr(sample)}'

print('PASS: Lexer word immutability verified for all samples.')
"
```

---

## 3. PARSER SERVICE VERIFICATION

**File:** `backend/services/formatting/parser_service.py`

### 3.1 Model loading — cached once

```bash
python -c "
import time
from services.formatting.parser_service import parse_lines

# First call (model loads)
start = time.perf_counter()
result1 = parse_lines(['Hello world.'])
t1 = time.perf_counter() - start

# Second call (model cached via lru_cache)
start = time.perf_counter()
result2 = parse_lines(['Another sentence here.'])
t2 = time.perf_counter() - start

print(f'First parse call:  {t1*1000:.0f}ms (model load + parse)')
print(f'Second parse call: {t2*1000:.0f}ms (model cached + parse)')
assert t2 < t1, 'WARN: Second call was not faster than first (lru_cache may not be working)'
print('PASS: Model caching appears to work')
"
```

### 3.2 Signal correctness — list items

```bash
python -c "
from services.formatting.parser_service import parse_lines

# List item detection tests
list_cases = [
    '- first item',       # dash bullet
    '* second item',      # asterisk bullet  
    '• third item',       # unicode bullet
    '1. numbered item',   # numbered list
    '2) another numbered',# numbered with paren
]

non_list_cases = [
    'This is a regular sentence.',
    'NotesFlare is a product name',
    'The quick brown fox jumps',
]

signals = parse_lines(list_cases)
for i, sig in enumerate(signals):
    assert sig['is_list_item_candidate'], f'FAIL: \"{list_cases[i]}\" not detected as list item. Signal: {sig}'
    print(f'PASS list: \"{list_cases[i]}\"')

signals = parse_lines(non_list_cases)
for i, sig in enumerate(signals):
    assert not sig['is_list_item_candidate'], f'FAIL: \"{non_list_cases[i]}\" incorrectly detected as list item'
    print(f'PASS non-list: \"{non_list_cases[i]}\"')
"
```

### 3.3 Signal correctness — heading detection

```bash
python -c "
from services.formatting.parser_service import parse_lines

# Lines that SHOULD be detected as heading candidates
# (short, no verb, no end punctuation)
heading_cases = [
    'Project Notes',          # 2 words, no verb
    'Key Observations',       # 2 words, noun-only
    'Three Main Topics',      # 3 words, no verb
]

# Lines that should NOT be detected as headings
non_heading_cases = [
    'This is a complete sentence with a verb.',   # has verb + punctuation
    'I am thinking about this problem deeply',    # has verb
    '- list item here',                           # list item
]

# NOTE: Heading detection is heuristic. Some edge cases may vary.
# Test only clear-cut cases.

heading_signals = parse_lines(heading_cases)
for i, sig in enumerate(heading_signals):
    if not sig['is_heading_candidate']:
        print(f'WARN: \"{heading_cases[i]}\" not detected as heading (check token count: {sig[\"token_count\"]})')
    else:
        print(f'PASS heading: \"{heading_cases[i]}\"')

non_heading_signals = parse_lines(non_heading_cases)
for i, sig in enumerate(non_heading_signals):
    if sig['is_heading_candidate']:
        print(f'WARN: \"{non_heading_cases[i]}\" unexpectedly detected as heading')
    else:
        print(f'PASS non-heading: \"{non_heading_cases[i]}\"')
"
```

### 3.4 Protected token detection

```bash
python -c "
from services.formatting.parser_service import parse_lines, PROTECTED_TOKENS

# Lines containing protected tokens
protected_lines = [
    'NotesFlare is a thought capture system',
    'MiniLM handles the embeddings',
    'spaCy parses the sentences',
    'Flareon is the domain container',
]

signals = parse_lines(protected_lines)
for i, sig in enumerate(signals):
    assert sig['contains_protected_token'], (
        f'FAIL: \"{protected_lines[i]}\" did not detect protected token. '
        f'Protected tokens: {PROTECTED_TOKENS}'
    )
    print(f'PASS protected: \"{protected_lines[i]}\"')

# Lines with no protected tokens
clean_lines = [
    'The weather is nice today',
    'I have three main points to make',
    'Consider the following observations',
]

signals = parse_lines(clean_lines)
for i, sig in enumerate(signals):
    assert not sig['contains_protected_token'], (
        f'FAIL: \"{clean_lines[i]}\" incorrectly flagged protected token'
    )
    print(f'PASS no-protected: \"{clean_lines[i]}\"')
"
```

### 3.5 Signal shape contract

Every signal dict from `parse_lines` must have exactly these keys:

```bash
python -c "
from services.formatting.parser_service import parse_lines

REQUIRED_KEYS = {
    'line_index', 'text', 'is_sentence_start', 'is_sentence_end',
    'is_list_item_candidate', 'is_heading_candidate', 'is_quote_candidate',
    'has_conjunction_start', 'token_count', 'contains_protected_token',
}

test_lines = [
    'Hello world.',
    '',                     # empty line
    '- list item',
    'And this continues',
]

signals = parse_lines(test_lines)
assert len(signals) == len(test_lines), f'Expected {len(test_lines)} signals, got {len(signals)}'

for i, sig in enumerate(signals):
    missing = REQUIRED_KEYS - set(sig.keys())
    extra = set(sig.keys()) - REQUIRED_KEYS
    assert not missing, f'Signal {i} missing keys: {missing}'
    # Extra keys are allowed — warning only
    if extra:
        print(f'WARN: Signal {i} has extra keys: {extra}')
    assert sig['line_index'] == i, f'line_index mismatch at {i}: {sig[\"line_index\"]}'
    assert isinstance(sig['token_count'], int), f'token_count must be int'
    assert isinstance(sig['is_list_item_candidate'], bool)
    assert isinstance(sig['is_heading_candidate'], bool)
    assert isinstance(sig['contains_protected_token'], bool)

print(f'PASS: All {len(signals)} signal shapes are correct.')
"
```

---

## 4. CHUNKER SERVICE VERIFICATION

**File:** `backend/services/formatting/chunker_service.py`

### 4.1 Basic chunking behavior

```bash
python -c "
from services.formatting.chunker_service import chunk_lines

# Test 1: Empty input
result = chunk_lines([])
assert result == [], f'FAIL: empty input should return empty list, got {result}'
print('PASS: Empty input returns []')

# Test 2: Short content stays in one chunk
short_lines = ['hello', 'world', 'this is short']
result = chunk_lines(short_lines)
assert len(result) == 1, f'FAIL: short content should be 1 chunk, got {len(result)}'
assert result[0]['chunk_index'] == 0
assert result[0]['lines'] == short_lines
print('PASS: Short content stays in one chunk')

# Test 3: Chunk dict has required keys
required_keys = {'chunk_index', 'lines', 'line_indices', 'char_start', 'char_end'}
for chunk in result:
    missing = required_keys - set(chunk.keys())
    assert not missing, f'Chunk missing keys: {missing}'
print('PASS: Chunk dict shape is correct')

# Test 4: line_indices are correct
result = chunk_lines(['a', 'b', 'c'])
assert result[0]['line_indices'] == [0, 1, 2], f'FAIL: {result[0][\"line_indices\"]}'
print('PASS: line_indices are zero-based and correct')
"
```

### 4.2 Overlap behavior

```bash
python -c "
from services.formatting.chunker_service import chunk_lines

# Generate content long enough to force multiple chunks
# Default chunk_size=800, overlap=150
# Generate ~900 chars across lines to force a split

long_lines = [f'This is line {i} with some content to fill up space for chunking tests here' for i in range(15)]
result = chunk_lines(long_lines, chunk_size=200, overlap=40)

print(f'Total lines: {len(long_lines)}')
print(f'Chunks produced: {len(result)}')

assert len(result) > 1, 'FAIL: Expected multiple chunks with chunk_size=200'

# Verify overlap: last lines of chunk N should appear in chunk N+1
for i in range(len(result) - 1):
    current_indices = set(result[i]['line_indices'])
    next_indices = set(result[i+1]['line_indices'])
    overlap = current_indices & next_indices
    print(f'Chunk {i} -> Chunk {i+1}: overlap line indices = {sorted(overlap)}')
    # Overlap may be 0 for very short individual lines — this is acceptable

# Verify all original lines appear in at least one chunk
all_covered = set()
for chunk in result:
    all_covered.update(chunk['line_indices'])
expected = set(range(len(long_lines)))
missing = expected - all_covered
assert not missing, f'FAIL: Lines not covered by any chunk: {missing}'
print('PASS: All lines covered by at least one chunk')
print('PASS: Multi-chunk behavior verified')
"
```

### 4.3 Chunk boundaries never cross burst boundaries

This is an architectural guarantee. The chunker only receives lines from a SINGLE burst. The verification is that the pipeline always calls `chunk_lines` per-burst, not per-Flareon. This is enforced in `formatting_routes.py`:

```bash
# Verify in formatting_routes.py that chunking is called INSIDE the route handler
# after burst text reconstruction — not on the full Flareon content.

python -c "
import ast, pathlib

source = pathlib.Path('api/formatting_routes.py').read_text()
tree = ast.parse(source)

# Find chunk_lines call site and verify it's within format_burst function
found_in_format = False
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'format_burst':
        func_source = ast.get_source_segment(source, node)
        if 'chunk_lines' in func_source:
            found_in_format = True
            break

assert found_in_format, 'FAIL: chunk_lines not called inside format_burst function'
print('PASS: chunk_lines is called inside format_burst (per-burst scope)')
"
```

---

## 5. EMBEDDING SERVICE VERIFICATION

**File:** `backend/services/formatting/embedding_service.py`

### 5.1 Output shape and dtype

```bash
python -c "
import numpy as np
from services.formatting.embedding_service import embed_lines, compute_similarity_sequence

# Test: Shape
lines = ['Hello world', 'This is a test sentence', 'And here is another one']
embeddings = embed_lines(lines)

print(f'Input lines: {len(lines)}')
print(f'Embedding shape: {embeddings.shape}')
print(f'Embedding dtype: {embeddings.dtype}')

assert embeddings.shape == (3, 384), f'Expected (3, 384), got {embeddings.shape}'
assert embeddings.dtype == np.float32, f'Expected float32, got {embeddings.dtype}'
print('PASS: Embedding shape and dtype correct')
"
```

### 5.2 Empty line handling

```bash
python -c "
import numpy as np
from services.formatting.embedding_service import embed_lines

# Empty lines should get zero vectors
lines = ['hello', '', 'world']
embeddings = embed_lines(lines)

assert embeddings.shape == (3, 384), f'Shape error: {embeddings.shape}'
# Empty line (index 1) should have zero embedding
assert np.allclose(embeddings[1], 0), f'FAIL: Empty line embedding not zero. Got: {embeddings[1][:5]}'
# Non-empty lines should have non-zero embeddings
assert not np.allclose(embeddings[0], 0), 'FAIL: Non-empty line has zero embedding'
assert not np.allclose(embeddings[2], 0), 'FAIL: Non-empty line has zero embedding'
print('PASS: Empty lines get zero embeddings')
print('PASS: Non-empty lines get non-zero embeddings')
"
```

### 5.3 Cosine similarity range and semantic ordering

```bash
python -c "
import numpy as np
from services.formatting.embedding_service import embed_lines, compute_similarity_sequence

# Semantically similar consecutive pairs should have higher similarity
# than semantically different pairs

lines = [
    'The dog ran across the field',        # line 0
    'The puppy sprinted through the grass', # line 1 — similar to 0
    'Quantum mechanics defines wave functions', # line 2 — different topic
    'Particles exhibit wave-particle duality',  # line 3 — similar to 2
]

embeddings = embed_lines(lines)
similarities = compute_similarity_sequence(embeddings)

print(f'Similarities: {[round(s, 3) for s in similarities]}')
print(f'  0→1 (similar dogs): {similarities[0]:.3f}')
print(f'  1→2 (topic switch): {similarities[1]:.3f}')
print(f'  2→3 (similar physics): {similarities[2]:.3f}')

# All similarities should be in [-1, 1]
for s in similarities:
    assert -1.0 <= s <= 1.0, f'FAIL: similarity out of range: {s}'

# 0→1 should be more similar than 1→2 (topic switch)
assert similarities[0] > similarities[1], (
    f'FAIL: similar dog sentences ({similarities[0]:.3f}) should be more similar '
    f'than topic switch ({similarities[1]:.3f})'
)
print('PASS: Semantic ordering correct — similar content has higher similarity')
print('PASS: All similarities in range [-1, 1]')
"
```

### 5.4 Similarity sequence length

```bash
python -c "
from services.formatting.embedding_service import embed_lines, compute_similarity_sequence

# Similarity sequence length must be len(lines) - 1
for n in [1, 2, 3, 5, 10]:
    lines = [f'Line number {i} with some content here' for i in range(n)]
    embeddings = embed_lines(lines)
    similarities = compute_similarity_sequence(embeddings)
    expected_len = max(0, n - 1)
    assert len(similarities) == expected_len, (
        f'FAIL: n={n} lines → expected {expected_len} similarities, got {len(similarities)}'
    )
    print(f'PASS: {n} lines → {len(similarities)} similarities')
"
```

### 5.5 Model loading is cached (lru_cache)

```bash
python -c "
import time
from services.formatting.embedding_service import embed_lines

# First call
start = time.perf_counter()
e1 = embed_lines(['test sentence one'])
t1 = time.perf_counter() - start

# Second call — should be much faster (model cached)
start = time.perf_counter()
e2 = embed_lines(['test sentence two'])
t2 = time.perf_counter() - start

print(f'First embed call:  {t1*1000:.0f}ms')
print(f'Second embed call: {t2*1000:.0f}ms')
print(f'Speedup: {t1/t2:.1f}x' if t2 > 0 else 'Speedup: inf')
assert t2 < t1, 'WARN: Second call not faster — lru_cache may not be working'
print('PASS: Model caching working (second call faster)')
"
```

### 5.6 Graceful failure when model unavailable

```bash
python -c "
# Simulate embedding failure — the pipeline should continue with rule-only formatting
from services.formatting.embedding_service import embed_lines
from unittest.mock import patch

with patch('services.formatting.embedding_service._load_model', side_effect=RuntimeError('Model not found')):
    try:
        result = embed_lines(['test'])
        print('WARN: Expected exception not raised')
    except Exception as e:
        print(f'PASS: Exception raised correctly: {type(e).__name__}: {e}')

# Verify the API route catches this gracefully
# (The try/except block in formatting_routes.py format_burst)
print('Verify: formatting_routes.py has try/except around embedding calls')
import pathlib
source = pathlib.Path('api/formatting_routes.py').read_text()
assert 'except Exception' in source or 'except' in source, 'FAIL: No exception handling in route'
print('PASS: Exception handling present in route')
"
```

---

## 6. FORMATTER SERVICE VERIFICATION

**File:** `backend/services/formatting/formatter_service.py`

### 6.1 List item operations generated correctly

```bash
python -c "
from services.formatting.parser_service import parse_lines
from services.formatting.formatter_service import generate_operations

# Asterisk bullet should be normalized to dash
lines = ['* some item here', '* another item']
signals = parse_lines(lines)
ops = generate_operations(signals)

print(f'Operations generated: {len(ops)}')
for op in ops:
    print(f'  line {op[\"line_index\"]}: {op[\"operation\"]} | {repr(op[\"raw_before\"])} → {repr(op[\"formatted_after\"])}')

list_ops = [o for o in ops if o['operation'] == 'format_as_list_item']
assert len(list_ops) > 0, 'FAIL: No list_item operations generated for asterisk bullets'

for op in list_ops:
    assert op['formatted_after'].startswith('- '), (
        f'FAIL: List item not normalized to \"- \" prefix. Got: {repr(op[\"formatted_after\"])}'
    )
print('PASS: Asterisk bullets normalized to dash prefix')
"
```

### 6.2 No operation generated when already formatted

```bash
python -c "
from services.formatting.parser_service import parse_lines
from services.formatting.formatter_service import generate_operations

# Already correct dash bullets should not generate operations
lines = ['- already correct', '- also correct']
signals = parse_lines(lines)
ops = generate_operations(signals)

list_ops = [o for o in ops if o['operation'] == 'format_as_list_item']
# If the line is already '- item', formatter should detect no change needed
print(f'Operations for already-formatted bullets: {list_ops}')
print('NOTE: This is acceptable if 0 ops. If ops present, verify formatted_after != raw_before.')
for op in list_ops:
    assert op['formatted_after'] != op['raw_before'], (
        'FAIL: Operation generated where formatted == raw (no-op operation)'
    )
print('PASS: No no-op operations generated')
"
```

### 6.3 Protected token lines skipped

```bash
python -c "
from services.formatting.parser_service import parse_lines
from services.formatting.formatter_service import generate_operations

# Single-word or two-word lines with protected tokens should not be formatted
protected_lines = [
    'NotesFlare',
    'MiniLM Burst',
]
signals = parse_lines(protected_lines)
ops = generate_operations(signals)

# These should produce no operations (protected + short)
print(f'Ops for protected token lines: {ops}')
assert len(ops) == 0, f'FAIL: Operations generated for protected token lines: {ops}'
print('PASS: Protected token short lines skipped')
"
```

### 6.4 Paragraph break detection with similarity

```bash
python -c "
from services.formatting.formatter_service import generate_operations, TOPIC_BREAK_THRESHOLD

# Simulate signals for two lines with a topic transition
signals = [
    {
        'line_index': 0, 'text': 'First topic about cooking recipes',
        'is_sentence_start': True, 'is_sentence_end': True,
        'is_list_item_candidate': False, 'is_heading_candidate': False,
        'is_quote_candidate': False, 'has_conjunction_start': False,
        'token_count': 5, 'contains_protected_token': False,
    },
    {
        'line_index': 1, 'text': 'Quantum physics equations derivation',
        'is_sentence_start': True, 'is_sentence_end': True,
        'is_list_item_candidate': False, 'is_heading_candidate': False,
        'is_quote_candidate': False, 'has_conjunction_start': False,
        'token_count': 4, 'contains_protected_token': False,
    },
]

# Similarity below threshold triggers paragraph break
low_similarity = [TOPIC_BREAK_THRESHOLD - 0.1]
ops = generate_operations(signals, similarity_scores=low_similarity)

para_ops = [o for o in ops if o['operation'] == 'insert_paragraph_break']
print(f'Paragraph break ops (low similarity): {len(para_ops)}')
assert len(para_ops) > 0, (
    f'FAIL: Paragraph break not generated for similarity {low_similarity[0]:.2f} < threshold {TOPIC_BREAK_THRESHOLD}'
)
print('PASS: Paragraph break generated on low similarity')

# High similarity should NOT trigger paragraph break
high_similarity = [TOPIC_BREAK_THRESHOLD + 0.1]
ops = generate_operations(signals, similarity_scores=high_similarity)
para_ops = [o for o in ops if o['operation'] == 'insert_paragraph_break']
assert len(para_ops) == 0, (
    f'FAIL: Paragraph break generated for high similarity {high_similarity[0]:.2f}'
)
print('PASS: No paragraph break for high similarity')
"
```

### 6.5 Operation dict shape contract

```bash
python -c "
from services.formatting.parser_service import parse_lines
from services.formatting.formatter_service import generate_operations

REQUIRED_OP_KEYS = {'line_index', 'operation', 'raw_before', 'formatted_after'}
VALID_OPERATIONS = {
    'insert_paragraph_break', 'insert_line_break',
    'format_as_list_item', 'format_as_heading',
    'format_as_quote', 'normalize_spacing'
}

lines = [
    '* item one',
    '* item two',
    'heading here',
    'A long regular sentence that is definitely more than twelve tokens long and continues',
    'And this begins with conjunction after a very long previous line',
]
signals = parse_lines(lines)
ops = generate_operations(signals)

print(f'Total operations generated: {len(ops)}')
for op in ops:
    missing = REQUIRED_OP_KEYS - set(op.keys())
    assert not missing, f'Op missing keys: {missing}. Op: {op}'
    assert op['operation'] in VALID_OPERATIONS, f'Invalid operation type: {op[\"operation\"]}'
    assert op['formatted_after'] != op['raw_before'], f'No-op detected: {op}'
    print(f'  PASS: {op[\"operation\"]} at line {op[\"line_index\"]}')

print('PASS: All operation shapes valid')
"
```

---

## 7. DIFF SERVICE VERIFICATION

**File:** `backend/services/formatting/diff_service.py`

### 7.1 Diffs stored correctly and retrievable

```bash
# Start backend first: python main.py &
# Then run:

curl -s -X POST http://localhost:8000/api/flareons \
  -H "Content-Type: application/json" \
  -d '{"name": "NLP Verification Test"}' | python -c "
import json, sys
data = json.load(sys.stdin)
print('Flareon created:', data['id'], data['name'])
"

# Then in Python directly (requires running backend context):
python -c "
from database.db import init_db, get_db

init_db()
db = get_db()

# Verify tables exist
tables = [r['name'] for r in db.execute(
    \"SELECT name FROM sqlite_master WHERE type='table'\"
).fetchall()]

required = ['burst_lines', 'burst_diffs', 'line_history']
for t in required:
    assert t in tables, f'FAIL: Table {t} missing. Found: {tables}'
    print(f'PASS: Table {t} exists')
"
```

### 7.2 Pending-only clearing on re-format

This is the most critical correctness property of the diff service:

```bash
python -c "
# This test requires a live DB. Run from backend/ directory.
# Assumes a burst with ID 1 already exists and has content.

from database.db import init_db, get_db
from services.formatting.diff_service import store_diffs, accept_diff, get_diffs_for_burst
import uuid

init_db()
db = get_db()

# Check we have a burst_lines entry to work with
lines = db.execute('SELECT * FROM burst_lines LIMIT 1').fetchone()
if not lines:
    print('SKIP: No burst_lines rows found. Run POST /api/format/burst first to populate.')
else:
    line_id = lines['line_id']
    burst_id = lines['burst_id']
    
    # Create a test diff directly
    diff_id_accepted = str(uuid.uuid4())
    diff_id_pending = str(uuid.uuid4())
    
    db.execute(
        '''INSERT INTO burst_diffs (diff_id, burst_id, line_id, operation, status, raw_before, formatted_after, created_at, updated_at)
           VALUES (?, ?, ?, 'format_as_list_item', 'accepted', 'test', '- test', datetime('now'), datetime('now'))''',
        (diff_id_accepted, burst_id, line_id)
    )
    db.execute(
        '''INSERT INTO burst_diffs (diff_id, burst_id, line_id, operation, status, raw_before, formatted_after, created_at, updated_at)
           VALUES (?, ?, ?, 'format_as_list_item', 'pending', 'test2', '- test2', datetime('now'), datetime('now'))''',
        (diff_id_pending, burst_id, line_id)
    )
    db.commit()
    
    # Now simulate store_diffs (which clears only pending)
    store_diffs(burst_id, [], [])  # Empty ops — just triggers pending clear
    
    # Accepted diff should still exist
    accepted_row = db.execute(
        'SELECT * FROM burst_diffs WHERE diff_id = ?', (diff_id_accepted,)
    ).fetchone()
    assert accepted_row is not None, 'FAIL: Accepted diff was deleted!'
    assert accepted_row['status'] == 'accepted', f'FAIL: Accepted diff status changed to {accepted_row[\"status\"]}'
    
    # Pending diff should be gone
    pending_row = db.execute(
        'SELECT * FROM burst_diffs WHERE diff_id = ?', (diff_id_pending,)
    ).fetchone()
    assert pending_row is None, 'FAIL: Pending diff was NOT deleted on re-format!'
    
    # Cleanup test data
    db.execute('DELETE FROM burst_diffs WHERE diff_id = ?', (diff_id_accepted,))
    db.commit()
    
    print('PASS: Accepted diffs preserved on re-format')
    print('PASS: Pending diffs cleared on re-format')
"
```

### 7.3 Line history is immutable (insert-only)

```bash
python -c "
import pathlib

# Verify there is no UPDATE or DELETE on line_history in any service file
service_files = list(pathlib.Path('services/formatting').glob('*.py'))

for filepath in service_files:
    source = filepath.read_text()
    source_upper = source.upper()
    
    # Check for dangerous patterns
    if 'UPDATE LINE_HISTORY' in source_upper:
        print(f'FAIL: {filepath.name} contains UPDATE on line_history')
    elif 'DELETE FROM LINE_HISTORY' in source_upper:
        print(f'FAIL: {filepath.name} contains DELETE on line_history')
    else:
        print(f'PASS: {filepath.name} does not mutate line_history')
"
```

---

## 8. LINEAGE SERVICE VERIFICATION

**File:** `backend/services/formatting/lineage_service.py`

### 8.1 Stable IDs across re-formats

```bash
python -c "
# This test requires an initialized DB.
from database.db import init_db, get_db
from services.formatting.lineage_service import get_or_create_lines, compute_checksum

init_db()

# Use a fake burst_id that won't conflict
# (For isolated testing only — not used in production)
import uuid

# Simulate first format
lines_v1 = ['hello world', 'this is line two', 'and line three']

# We need a real burst_id — use burst_id=999999 as a test sentinel
# First clean up any leftovers
db = get_db()
db.execute('DELETE FROM burst_lines WHERE burst_id = 999999')
db.commit()

# Insert test burst if needed (bypass FK constraint for testing only)
# In real operation, bursts table must have this ID.
# For test isolation, check if we can proceed:
burst_exists = db.execute('SELECT id FROM bursts WHERE id = 999999').fetchone()
if not burst_exists:
    print('SKIP: No burst 999999 in DB. Use API to create a real burst for this test.')
else:
    result_first = get_or_create_lines(999999, lines_v1)
    ids_first = [r['line_id'] for r in result_first]
    
    # Second call with same content — IDs must be stable
    result_second = get_or_create_lines(999999, lines_v1)
    ids_second = [r['line_id'] for r in result_second]
    
    assert ids_first == ids_second, (
        f'FAIL: Line IDs changed on re-format!\\n  First:  {ids_first}\\n  Second: {ids_second}'
    )
    print('PASS: Line IDs are stable across re-formats for unchanged content')
    
    # Changed content gets new IDs
    lines_v2 = ['hello world', 'THIS LINE CHANGED', 'and line three']
    result_third = get_or_create_lines(999999, lines_v2)
    ids_third = [r['line_id'] for r in result_third]
    
    # Line 0 and 2 unchanged — IDs should match
    assert ids_first[0] == ids_third[0], 'FAIL: Unchanged line 0 got new ID'
    assert ids_first[2] == ids_third[2], 'FAIL: Unchanged line 2 got new ID'
    # Line 1 changed — should get new ID
    assert ids_first[1] != ids_third[1], 'FAIL: Changed line 1 kept old ID'
    print('PASS: Changed lines get new IDs; unchanged lines keep stable IDs')
    
    # Cleanup
    db.execute('DELETE FROM burst_lines WHERE burst_id = 999999')
    db.commit()
"
```

### 8.2 Checksum consistency

```bash
python -c "
from services.formatting.lineage_service import compute_checksum

# Same content always produces same checksum
line = 'hello world this is consistent'
assert compute_checksum(line) == compute_checksum(line), 'FAIL: Checksum not deterministic'
print('PASS: Checksum is deterministic')

# Different content produces different checksum
assert compute_checksum('line one') != compute_checksum('line two'), 'FAIL: Different lines same checksum'
print('PASS: Different lines produce different checksums')

# Checksum is a hex string of length 64 (SHA-256)
result = compute_checksum('test')
assert len(result) == 64 and all(c in '0123456789abcdef' for c in result), (
    f'FAIL: Checksum not valid SHA-256 hex: {result}'
)
print('PASS: Checksum is valid SHA-256 hex (64 chars)')
"
```

---

## 9. FULL PIPELINE END-TO-END VERIFICATION

### 9.1 Pipeline stages all fire in order

```bash
# Requires running backend (python main.py)

python -c "
import requests, json

BASE = 'http://localhost:8000/api'

# Step 1: Create Flareon
r = requests.post(f'{BASE}/flareons', json={'name': 'NLP E2E Test'})
assert r.status_code == 200, f'Create flareon failed: {r.text}'
flareon_id = r.json()['id']
print(f'Flareon ID: {flareon_id}')

# Step 2: Open Flareon (creates burst)
r = requests.get(f'{BASE}/session/switch/{flareon_id}')
assert r.status_code == 200, f'Switch flareon failed: {r.text}'
burst_id = r.json()['burst_id']
print(f'Burst ID: {burst_id}')

# Step 3: Append multi-structural content
content = '''this is a first thought about the project
and here is a second thought continuing
- need embeddings
- need chunking  
- need vector cache
some final reflection on the nature of thought capture'''

r = requests.post(f'{BASE}/burst/append', json={'burst_id': burst_id, 'text': content})
assert r.status_code == 200, f'Append failed: {r.text}'
print('Content appended')

# Step 4: Format
r = requests.post(f'{BASE}/format/burst', json={'burst_id': burst_id})
assert r.status_code == 200, f'Format failed: {r.text}'

result = r.json()
print(f'Format result:')
print(f'  burst_id: {result[\"burst_id\"]}')
print(f'  lines: {len(result[\"lines\"])}')
print(f'  diffs: {result[\"diff_count\"]}')
print(f'  processed_at: {result[\"processed_at\"]}')

assert result['burst_id'] == burst_id
assert len(result['lines']) > 0, 'FAIL: No lines returned'
assert result['diff_count'] == len(result['diffs']), 'FAIL: diff_count mismatch'
assert result['processed_at'], 'FAIL: processed_at empty'

# Verify lines have required fields
for line in result['lines']:
    assert 'line_id' in line
    assert 'raw_line' in line
    assert 'status' in line
    assert line['status'] in ['untouched', 'pending', 'accepted', 'rejected']

print(f'PASS: Pipeline produced {result[\"diff_count\"]} diffs for structured content')
print(f'PASS: All line shapes valid')
"
```

### 9.2 Raw text sacred — never modified

```bash
python -c "
import requests

BASE = 'http://localhost:8000/api'

# Use existing burst from previous test or create a new one
r = requests.get(f'{BASE}/session/resume')
data = r.json()
burst_id = data.get('burst_id') or data.get('active_burst_id')
original_content = data.get('stream_content', '')

if not burst_id:
    print('SKIP: No active burst. Run the pipeline test first.')
else:
    # Get the formatted version
    r = requests.get(f'{BASE}/format/burst/{burst_id}')
    assert r.status_code == 200
    formatted = r.json()
    
    # The raw_text field must match original appended content
    print(f'raw_text length: {len(formatted[\"raw_text\"])}')
    print(f'formatted_text length: {len(formatted[\"formatted_text\"])}')
    
    # Accept all diffs
    r = requests.post(f'{BASE}/format/diff/accept-all', json={'burst_id': burst_id})
    
    # Re-fetch formatted burst
    r = requests.get(f'{BASE}/format/burst/{burst_id}')
    formatted_after = r.json()
    
    # raw_text must be identical before and after accepting
    assert formatted['raw_text'] == formatted_after['raw_text'], (
        'FAIL: raw_text changed after accepting diffs!'
    )
    print('PASS: raw_text is immutable — never changed by formatting pipeline')
    print('PASS: formatted_text may differ from raw_text (changes accepted)')
"
```

---

## 10. NLP PERFORMANCE BENCHMARKS

Run these benchmarks to establish baseline performance for V1.2.

```bash
python -c "
import time
import requests

BASE = 'http://localhost:8000/api'

# Benchmark: Format a burst (first call — models cold)
r = requests.get(f'{BASE}/session/resume')
burst_id = r.json().get('burst_id') or r.json().get('active_burst_id')

if not burst_id:
    print('SKIP: No active burst for benchmarking')
else:
    times = []
    for i in range(3):
        start = time.perf_counter()
        r = requests.post(f'{BASE}/format/burst', json={'burst_id': burst_id})
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)
        print(f'  Format call {i+1}: {elapsed*1000:.0f}ms')
    
    avg = sum(times) / len(times)
    print(f'Average format time: {avg:.0f}ms')
    
    # Targets from V1_2_FRONTEND.md Section 18
    if times[0] > 3000:
        print(f'WARN: First format call {times[0]:.0f}ms > 3000ms target (cold models)')
    if avg > 2000:
        print(f'WARN: Average {avg:.0f}ms > 2000ms. Check model caching.')
    else:
        print(f'PASS: Average format time {avg:.0f}ms within target')
"
```

---

## 11. FINAL NLP VERIFICATION CHECKLIST

Complete all items before declaring V1.2 NLP implementation done:

### Environment
- [ ] `python -m spacy download en_core_web_sm` completed without errors
- [ ] spaCy loads and processes a sentence in < 500ms cold
- [ ] MiniLM loads and embeds a sentence, shape is `(1, 384)`
- [ ] ONNX Runtime is available (at least CPUExecutionProvider)

### Lexer
- [ ] NFC normalization works on decomposed Unicode
- [ ] Windows line endings (`\r\n`) normalized to `\n`
- [ ] Trailing whitespace stripped per line
- [ ] 3+ consecutive blank lines collapsed to 2
- [ ] No words changed by lexer

### Parser
- [ ] `parse_lines([])` returns `[]`
- [ ] `parse_lines([''])` returns a signal with `token_count: 0`
- [ ] List items (`- `, `* `, `1. `) correctly detected
- [ ] Protected tokens (NotesFlare, MiniLM, spaCy, Flareon) detected
- [ ] Signal dict has all 10 required keys for every line

### Chunker
- [ ] Empty input returns `[]`
- [ ] Short content produces 1 chunk
- [ ] Long content (> `chunk_size` chars) produces multiple chunks with overlap
- [ ] Every original line appears in at least one chunk

### Embeddings
- [ ] Output shape is `(n_lines, 384)`
- [ ] Empty lines get zero vectors
- [ ] Similarity between semantically similar lines > between dissimilar lines
- [ ] Similarity sequence length is `n_lines - 1`
- [ ] Model loads once (second call significantly faster than first)

### Formatter
- [ ] `* item` normalized to `- item`
- [ ] Already-formatted `- item` generates no operation
- [ ] Short protected-token lines not formatted
- [ ] Low similarity → paragraph break operation
- [ ] High similarity → no paragraph break
- [ ] All operations have the 4 required keys and a valid operation type
- [ ] `formatted_after != raw_before` for every operation

### Diff Service
- [ ] `store_diffs` clears only PENDING diffs, not ACCEPTED or REJECTED
- [ ] `accept_diff` updates both `burst_diffs.status` and `burst_lines.formatted_line`
- [ ] `reject_diff` restores `formatted_line = raw_line`
- [ ] `line_history` only has INSERT operations (no UPDATE or DELETE in code)

### Lineage
- [ ] Same content → same `line_id` across re-formats
- [ ] Changed content → new `line_id`
- [ ] Checksum is deterministic SHA-256 (64 hex chars)

### Full Pipeline
- [ ] `POST /api/format/burst` returns `lines` + `diffs` for structured content
- [ ] `raw_text` field never changes after accepting diffs
- [ ] Re-format preserves accepted diffs, replaces pending
- [ ] `diff_count: 0` returned without error for uniform content

### Performance
- [ ] First format call < 3000ms (cold model load)
- [ ] Subsequent format calls < 2000ms (warm models)
- [ ] Accept/Reject single diff < 100ms (backend)
