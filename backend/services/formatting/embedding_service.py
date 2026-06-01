# services/formatting/embedding_service.py

"""
Embedding engine using MiniLM via sentence-transformers + ONNX Runtime.

CPU-first. ONNX Runtime will automatically use GPU/NPU if available.
Model is loaded lazily on first call — startup is not delayed.

Used for:
- Semantic similarity between consecutive lines
- Burst cohesion scoring
- Topic transition detection (sudden similarity drop)
"""

from functools import lru_cache
from typing import List
import numpy as np


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model():
    """Load sentence-transformers model. Cached — only loads once per process."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)
        return model
    except ImportError:
        raise RuntimeError(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )


def embed_lines(lines: list[str]) -> np.ndarray:
    """
    Compute embeddings for a list of lines.
    Returns a 2D numpy array of shape (len(lines), embedding_dim).
    Empty lines get zero vectors.
    """
    model = _load_model()

    non_empty_indices = [i for i, l in enumerate(lines) if l.strip()]
    non_empty_lines = [lines[i] for i in non_empty_indices]

    if not non_empty_lines:
        return np.zeros((len(lines), 384), dtype=np.float32)   # MiniLM embedding dim = 384

    embeddings = model.encode(non_empty_lines, convert_to_numpy=True)

    # Re-insert zero vectors for empty lines
    full_embeddings = np.zeros((len(lines), embeddings.shape[1]), dtype=np.float32)
    for result_idx, orig_idx in enumerate(non_empty_indices):
        full_embeddings[orig_idx] = embeddings[result_idx]

    return full_embeddings


def compute_similarity_sequence(embeddings: np.ndarray) -> list[float]:
    """
    Compute cosine similarity between each consecutive pair of line embeddings.
    Returns a list of floats of length len(embeddings) - 1.
    A sudden drop indicates a topic transition boundary.
    """
    if len(embeddings) < 2:
        return []

    similarities = []
    for i in range(len(embeddings) - 1):
        a, b = embeddings[i], embeddings[i + 1]
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            similarities.append(0.0)
        else:
            similarities.append(float(np.dot(a, b) / (norm_a * norm_b)))

    return similarities
