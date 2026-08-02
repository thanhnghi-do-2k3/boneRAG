"""Tiny in-memory vector index for Baseline."""

from __future__ import annotations

from dataclasses import dataclass

from .encoder import Vector


def dot(left: Vector, right: Vector) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions do not match")
    return sum(a * b for a, b in zip(left, right))


@dataclass(frozen=True)
class SearchHit:
    record_id: str
    score: float


class InMemoryVectorIndex:
    """Store vectors and return nearest records by cosine score.

    Because `HashingTextEncoder` already returns normalized vectors, dot product
    is equivalent to cosine similarity here.
    """

    def __init__(self) -> None:
        self._vectors: dict[str, Vector] = {}

    def add(self, record_id: str, vector: Vector) -> None:
        if self._vectors:
            first = next(iter(self._vectors.values()))
            if len(first) != len(vector):
                raise ValueError("all vectors in one index must share one dimension")
        self._vectors[record_id] = vector

    def search(self, query_vector: Vector, top_k: int = 4) -> list[SearchHit]:
        hits = [
            SearchHit(record_id=record_id, score=dot(query_vector, vector))
            for record_id, vector in self._vectors.items()
        ]
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]
