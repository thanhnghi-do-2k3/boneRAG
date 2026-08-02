"""Text encoder used by Baseline.

This is intentionally simple. It lets us demonstrate retrieval without model
weights. A production version should keep the same `encode(text)` method but use
BiomedCLIP, BGE-VL, or another medical multimodal encoder.
"""

from __future__ import annotations

import hashlib
import math
import re

Vector = tuple[float, ...]
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize(values: list[float]) -> Vector:
    """Return a unit-length vector so dot product behaves like cosine similarity."""

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return tuple(values)
    return tuple(value / norm for value in values)


class HashingTextEncoder:
    """Deterministic feature-hashing text encoder.

    Each token is hashed into one bucket. The bucket receives +1 or -1 depending
    on the hash. This is not semantic AI, but repeated medical keywords such as
    "wrist", "fracture", "radius" still make related records closer.
    """

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def tokenize(self, text: str) -> list[str]:
        return TOKEN_PATTERN.findall(text.lower())

    def encode(self, text: str) -> Vector:
        buckets = [0.0] * self.dim
        for token in self.tokenize(text):
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            buckets[index] += sign
        return normalize(buckets)
