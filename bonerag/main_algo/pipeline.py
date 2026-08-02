"""Baseline BoneRAG pipeline.

The goal is clarity over model quality. This file shows the minimum moving
parts behind an Image RAG system:

1. Build an index from an evidence corpus.
2. Encode the user question.
3. Retrieve candidate evidence.
4. Rerank with simple domain hints.
5. Generate an answer that cites retrieved evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterator

from .data import ImageRecord, SAMPLE_RECORDS
from .encoder import HashingTextEncoder
from .vector_index import InMemoryVectorIndex, SearchHit


@dataclass(frozen=True)
class Evidence:
    image_id: str
    title: str
    body_part: str
    diagnosis: str
    fracture_type: str
    region: str
    evidence_note: str
    retrieval_score: float
    rerank_score: float


@dataclass(frozen=True)
class PipelineResult:
    question: str
    used_retrieval: bool
    answer: str
    evidence: list[Evidence]
    debug: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "used_retrieval": self.used_retrieval,
            "answer": self.answer,
            "evidence": [asdict(item) for item in self.evidence],
            "debug": self.debug,
        }


class BoneRAGPipeline:
    """Small, dependency-free BoneRAG baseline."""

    def __init__(
        self,
        records: list[ImageRecord] | None = None,
        encoder: HashingTextEncoder | None = None,
        top_k: int = 4,
        min_similarity: float = 0.02,
    ) -> None:
        self.records = records or SAMPLE_RECORDS
        self.record_by_id = {record.image_id: record for record in self.records}
        self.encoder = encoder or HashingTextEncoder()
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.index = self._build_index()

    def _build_index(self) -> InMemoryVectorIndex:
        """Off-line phase: encode every record and add it to the vector index."""

        index = InMemoryVectorIndex()
        for record in self.records:
            index.add(record.image_id, self.encoder.encode(record.text))
        return index

    def retrieve(self, question: str) -> list[SearchHit]:
        """Online retrieval: encode the question and return top-k candidate ids."""

        query_vector = self.encoder.encode(question)
        return self.index.search(query_vector, top_k=self.top_k)

    def should_retrieve(self, question: str, hits: list[SearchHit]) -> bool:
        """Gate delta: skip evidence when the question is not image/medical specific."""

        if not hits:
            return False
        question_tokens = set(self.encoder.tokenize(question))
        medical_terms = {
            "xray",
            "x",
            "ray",
            "bone",
            "fracture",
            "gãy",
            "xương",
            "wrist",
            "hand",
            "hip",
            "tibia",
            "radius",
            "lesion",
            "tumor",
        }
        return bool(question_tokens & medical_terms) and hits[0].score >= self.min_similarity

    def rerank(self, question: str, hits: list[SearchHit]) -> list[Evidence]:
        """Light reranker phi: combine vector score with metadata keyword matches."""

        tokens = set(self.encoder.tokenize(question))
        evidence: list[Evidence] = []
        for hit in hits:
            record = self.record_by_id[hit.record_id]
            metadata_terms = {
                record.body_part.lower(),
                record.diagnosis.lower(),
                record.fracture_type.lower(),
                *self.encoder.tokenize(record.region),
            }
            overlap = len(tokens & metadata_terms)
            diagnosis_boost = 0.08 if record.diagnosis.lower() in tokens else 0.0
            body_part_boost = 0.05 if record.body_part.lower() in tokens else 0.0
            rerank_score = hit.score + 0.04 * overlap + diagnosis_boost + body_part_boost
            evidence.append(
                Evidence(
                    image_id=record.image_id,
                    title=record.title,
                    body_part=record.body_part,
                    diagnosis=record.diagnosis,
                    fracture_type=record.fracture_type,
                    region=record.region,
                    evidence_note=record.evidence_note,
                    retrieval_score=hit.score,
                    rerank_score=rerank_score,
                )
            )
        evidence.sort(key=lambda item: item.rerank_score, reverse=True)
        return evidence

    def generate_answer(self, question: str, evidence: list[Evidence], used_retrieval: bool) -> str:
        """Template generator used until a real MLLM is plugged in."""

        if not used_retrieval:
            return (
                "Baseline không tìm thấy bằng chứng ảnh đủ liên quan. "
                "Hệ thống nên hỏi thêm ảnh X-quang/câu hỏi cụ thể hơn thay vì đoán."
            )

        top = evidence[0]
        supporting = "; ".join(
            f"{item.title} ({item.body_part}, {item.diagnosis}, score={item.rerank_score:.3f})"
            for item in evidence[:3]
        )
        return (
            f"Câu hỏi: {question}\n\n"
            f"Kết luận Baseline: evidence gần nhất là '{top.title}', vùng {top.region}, "
            f"nhãn {top.diagnosis}. Ghi chú bằng chứng: {top.evidence_note}\n\n"
            f"Các ca được dùng để tham chiếu: {supporting}.\n\n"
            "Lưu ý: đây là baseline kỹ thuật để minh họa Image RAG, không phải chẩn đoán y khoa."
        )

    def answer(self, question: str) -> PipelineResult:
        """Run the full Baseline contract: q -> answer + evidence."""

        hits = self.retrieve(question)
        used_retrieval = self.should_retrieve(question, hits)
        evidence = self.rerank(question, hits) if used_retrieval else []
        answer = self.generate_answer(question, evidence, used_retrieval)
        return PipelineResult(
            question=question,
            used_retrieval=used_retrieval,
            answer=answer,
            evidence=evidence,
            debug={
                "top_k": self.top_k,
                "min_similarity": self.min_similarity,
                "raw_hits": [hit.__dict__ for hit in hits],
            },
        )

    def answer_events(self, question: str) -> Iterator[dict[str, object]]:
        """Yield explainable streaming events for the web UI.

        This is not token streaming from an LLM yet. It is pipeline streaming:
        each event tells the UI which BoneRAG stage just finished and carries
        the intermediate result needed to make the demo understandable.
        """

        yield {
            "type": "stage",
            "stage": "encode",
            "title": "Mã hóa câu hỏi",
            "message": "Biến câu hỏi thành vector truy vấn bằng HashingTextEncoder.",
        }
        hits = self.retrieve(question)
        yield {
            "type": "stage",
            "stage": "retrieve",
            "title": "Truy xuất top-k",
            "message": f"Lấy {len(hits)} ứng viên gần nhất từ InMemoryVectorIndex.",
            "hits": [hit.__dict__ for hit in hits],
        }

        used_retrieval = self.should_retrieve(question, hits)
        yield {
            "type": "stage",
            "stage": "gate",
            "title": "Cổng quyết định retrieval",
            "message": "Có đủ tín hiệu y khoa để dùng evidence." if used_retrieval else "Không đủ tín hiệu liên quan ảnh/xương, bỏ qua retrieval.",
            "used_retrieval": used_retrieval,
        }

        evidence = self.rerank(question, hits) if used_retrieval else []
        yield {
            "type": "stage",
            "stage": "rerank",
            "title": "Rerank evidence",
            "message": "Cộng thêm điểm body part, diagnosis và region để đẩy evidence hữu ích lên trước.",
            "evidence": [asdict(item) for item in evidence],
        }

        answer = self.generate_answer(question, evidence, used_retrieval)
        result = PipelineResult(
            question=question,
            used_retrieval=used_retrieval,
            answer=answer,
            evidence=evidence,
            debug={
                "top_k": self.top_k,
                "min_similarity": self.min_similarity,
                "raw_hits": [hit.__dict__ for hit in hits],
            },
        )
        for index, chunk in enumerate(self._chunk_text(answer, size=70)):
            yield {
                "type": "token",
                "index": index,
                "text": chunk,
            }
        yield {
            "type": "done",
            "result": result.to_dict(),
        }

    def _chunk_text(self, text: str, size: int) -> Iterator[str]:
        """Split text into readable chunks for simulated answer streaming."""

        words = text.split(" ")
        chunk = ""
        for word in words:
            next_chunk = f"{chunk} {word}".strip()
            if len(next_chunk) > size and chunk:
                yield chunk + " "
                chunk = word
            else:
                chunk = next_chunk
        if chunk:
            yield chunk

    def records_as_dicts(self) -> list[dict[str, str]]:
        return [asdict(record) for record in self.records]
