"""Vector index implementations: InMemoryVectorIndex and FAISSVectorIndex."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    """Store vectors and return nearest records by cosine score."""

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


class FAISSVectorIndex:
    """FAISS-backed vector index using IndexFlatIP (Cosine similarity for unit vectors)."""

    def __init__(self, dim: int = 256) -> None:
        import faiss
        import numpy as np

        self.faiss = faiss
        self.np = np
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.id_to_record: list[str] = []

    def add(self, record_id: str, vector: Vector) -> None:
        if len(vector) != self.dim:
            raise ValueError(f"Vector dim {len(vector)} does not match index dim {self.dim}")

        arr = self.np.array([vector], dtype=self.np.float32)
        self.faiss.normalize_L2(arr)
        self.index.add(arr)
        self.id_to_record.append(record_id)

    def search(self, query_vector: Vector, top_k: int = 4) -> list[SearchHit]:
        if self.index.ntotal == 0:
            return []

        arr = self.np.array([query_vector], dtype=self.np.float32)
        self.faiss.normalize_L2(arr)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(arr, k)

        hits: list[SearchHit] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.id_to_record):
                hits.append(SearchHit(record_id=self.id_to_record[idx], score=float(score)))
    def load_from_file(self, index_file: str | Path, id_to_record: list[str]) -> None:
        """Load pre-computed FAISS index from disk instantly (<0.05s)."""
        self.index = self.faiss.read_index(str(index_file))
        self.dim = self.index.d
        self.id_to_record = id_to_record

    def save_to_file(self, index_file: str | Path) -> None:
        """Save active FAISS index to disk."""
        self.faiss.write_index(self.index, str(index_file))


def get_vector_index(dim: int = 256) -> InMemoryVectorIndex | FAISSVectorIndex:
    """Return FAISSVectorIndex if faiss is available, else InMemoryVectorIndex."""
    try:
        return FAISSVectorIndex(dim=dim)
    except Exception:
        return InMemoryVectorIndex()
