"""Baseline & Multimodal BoneRAG pipeline.

Milestone 3 Architecture:
1. Multi-level indexing (Text Metadata + Full Image + ROI Fracture Crops).
2. BiomedCLIP / Multimodal vector encoder with fallback.
3. FAISS-backed Vector Index with fallback.
4. Domain-aware reranking & evidence grounding.
5. Pluggable generator (TemplateGenerator | GeminiGenerator | ...).
6. Research session logging & evaluation integration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

from .data import ImageRecord, SAMPLE_RECORDS
from .encoder import BaseMultimodalEncoder, get_multimodal_encoder
from .generator import AVAILABLE_GENERATORS, BaseGenerator, TemplateGenerator, get_generator
from .vector_index import FAISSVectorIndex, InMemoryVectorIndex, SearchHit, get_vector_index


@dataclass(frozen=True)
class Evidence:
    image_id: str
    image_path: str | None
    image_width: int | None
    image_height: int | None
    fracture_boxes: list[list[float]] | None
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
    """Multimodal BoneRAG pipeline with FAISS index, BiomedCLIP/ROI support & pluggable generator."""

    def __init__(
        self,
        records: list[ImageRecord] | None = None,
        encoder: BaseMultimodalEncoder | None = None,
        generator: BaseGenerator | None = None,
        top_k: int = 4,
        min_similarity: float = 0.02,
    ) -> None:
        self.records = records or SAMPLE_RECORDS
        self.record_by_id = {record.image_id: record for record in self.records}
        self.encoder = encoder or get_multimodal_encoder(mode="auto")
        self.generator = generator or TemplateGenerator()
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.index = self._build_index()

    def _build_index(self) -> InMemoryVectorIndex | FAISSVectorIndex:
        """Off-line phase: multi-level indexing (Text Metadata + Full Image + ROI Crops)."""

        dim = getattr(self.encoder, "dim", 256)
        index = get_vector_index(dim=dim)
        for record in self.records:
            # 1. Text metadata vector
            index.add(record.image_id, self.encoder.encode_text(record.text))

            # 2. Full Image vector (if image file exists)
            if record.image_path and Path(record.image_path).exists():
                try:
                    img_vec = self.encoder.encode_image(record.image_path)
                    index.add(f"{record.image_id}#image", img_vec)
                except Exception:
                    pass

                # 3. ROI Crop vectors (if fracture boxes exist)
                if record.fracture_boxes:
                    for i, bbox in enumerate(record.fracture_boxes):
                        try:
                            roi_vec = self.encoder.encode_roi(record.image_path, bbox)
                            index.add(f"{record.image_id}#roi_{i}", roi_vec)
                        except Exception:
                            pass
        return index

    def records_as_dicts(self) -> list[dict[str, object]]:
        """Expose the demo corpus in a JSON-friendly form for the server/UI."""

        return [asdict(record) for record in self.records]

    def retrieve(self, question: str) -> list[SearchHit]:
        """Online retrieval: encode the question and search multi-level index."""

        query_vector = self.encoder.encode_text(question)
        raw_hits = self.index.search(query_vector, top_k=self.top_k * 3)

        # Merge hits by parent record_id
        best_hits_by_parent: dict[str, tuple[float, str]] = {}
        for hit in raw_hits:
            parts = hit.record_id.split("#")
            parent_id = parts[0]
            match_type = parts[1] if len(parts) > 1 else "text_metadata"

            if parent_id not in self.record_by_id:
                continue

            if parent_id not in best_hits_by_parent or hit.score > best_hits_by_parent[parent_id][0]:
                best_hits_by_parent[parent_id] = (hit.score, match_type)

        merged_hits = [
            SearchHit(record_id=parent_id, score=score)
            for parent_id, (score, _) in best_hits_by_parent.items()
        ]
        merged_hits.sort(key=lambda item: item.score, reverse=True)
        return merged_hits[: self.top_k]

    def should_retrieve(self, question: str, hits: list[SearchHit]) -> bool:
        """Gate delta: skip evidence when the question is not image/medical specific."""

        if not hits:
            return False

        lower_q = question.lower()
        if "selected image context:" in lower_q or "image_id:" in lower_q:
            return True

        question_tokens = set(self.encoder.tokenize(question)) if hasattr(self.encoder, "tokenize") else set(lower_q.split())
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
            "bệnh",
            "ảnh",
            "bị",
            "gì",
            "thế",
            "chẩn",
            "đoán",
            "tổn",
            "thương",
            "vùng",
            "khớp",
            "xem",
            "này",
        }
        return bool(question_tokens & medical_terms) and hits[0].score >= self.min_similarity

    def rerank(self, question: str, hits: list[SearchHit]) -> list[Evidence]:
        """Light reranker phi: combine vector score with metadata keyword matches."""

        tokens = set(self.encoder.tokenize(question)) if hasattr(self.encoder, "tokenize") else set(question.lower().split())
        evidence: list[Evidence] = []
        for hit in hits:
            record = self.record_by_id[hit.record_id]
            tokenize_fn = getattr(self.encoder, "tokenize", lambda s: s.lower().split())
            metadata_terms = {
                record.body_part.lower(),
                record.diagnosis.lower(),
                record.fracture_type.lower(),
                *tokenize_fn(record.region),
            }
            overlap = len(tokens & metadata_terms)
            diagnosis_boost = 0.08 if record.diagnosis.lower() in tokens else 0.0
            body_part_boost = 0.05 if record.body_part.lower() in tokens else 0.0
            rerank_score = hit.score + 0.04 * overlap + diagnosis_boost + body_part_boost
            evidence.append(
                Evidence(
                    image_id=record.image_id,
                    image_path=record.image_path,
                    image_width=record.image_width,
                    image_height=record.image_height,
                    fracture_boxes=record.fracture_boxes,
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
        """Delegate answer generation to the plugged-in generator."""
        return self.generator.generate(question, evidence, used_retrieval)

    def answer(self, question: str) -> PipelineResult:
        """Run the full Baseline contract: q -> answer + evidence."""

        hits = self.retrieve(question)
        used_retrieval = self.should_retrieve(question, hits)
        evidence = self.rerank(question, hits) if used_retrieval else []
        answer = self.generate_answer(question, evidence, used_retrieval=used_retrieval)

        return PipelineResult(
            question=question,
            used_retrieval=used_retrieval,
            answer=answer,
            evidence=evidence,
            debug={
                "encoder_type": self.encoder.__class__.__name__,
                "generator_type": self.generator.name,
                "index_type": self.index.__class__.__name__,
                "raw_hits": [asdict(hit) for hit in hits],
                "top_hit_score": hits[0].score if hits else 0.0,
                "evidence_count": len(evidence),
                "model_config": {
                    "encoder": self.encoder.__class__.__name__,
                    "generator": self.generator.name,
                    "top_k": self.top_k,
                    "min_similarity": self.min_similarity,
                },
            },
        )

    def answer_events(self, question: str) -> Iterator[dict[str, object]]:
        """Alias for stream_answer used by HTTP server."""
        return self.stream_answer(question)

    def stream_answer(self, question: str) -> Iterator[dict[str, object]]:
        """Simulate an online response stream over Server-Sent Events."""

        yield {"type": "stage", "stage": "receive-question", "message": f"Nhận câu hỏi: {question}"}
        yield {
            "type": "stage",
            "stage": "encode-question",
            "message": f"Mã hóa bằng {self.encoder.__class__.__name__}",
        }

        hits = self.retrieve(question)
        yield {
            "type": "stage",
            "stage": "retrieve-hits",
            "message": f"Truy xuất được {len(hits)} ứng viên từ {self.index.__class__.__name__}",
            "hits": [asdict(hit) for hit in hits],
        }

        used = self.should_retrieve(question, hits)
        if not used:
            yield {
                "type": "stage",
                "stage": "gating-check",
                "message": "Cổng từ chối: câu hỏi không liên quan đến bằng chứng X-quang.",
            }
            refusal_answer = self.generate_answer(question, [], used_retrieval=False)
            chunk_size = 18
            for index in range(0, len(refusal_answer), chunk_size):
                yield {"type": "token", "text": refusal_answer[index : index + chunk_size]}

            final_result = PipelineResult(
                question=question,
                used_retrieval=False,
                answer=refusal_answer,
                evidence=[],
                debug={
                    "encoder_type": self.encoder.__class__.__name__,
                    "index_type": self.index.__class__.__name__,
                    "raw_hits": [asdict(hit) for hit in hits],
                    "top_hit_score": hits[0].score if hits else 0.0,
                    "evidence_count": 0,
                },
            )
            yield {"type": "done", "result": final_result.to_dict()}
            return

        yield {
            "type": "stage",
            "stage": "gating-check",
            "message": f"Cổng chấp nhận: điểm top hit={hits[0].score:.3f} >= {self.min_similarity}",
        }

        evidence = self.rerank(question, hits)
        yield {
            "type": "stage",
            "stage": "rerank-evidence",
            "message": f"Đã rerank {len(evidence)} bằng chứng theo vùng cơ thể & nhãn gãy",
        }

        full_answer = self.generate_answer(question, evidence, used_retrieval=True)
        chunk_size = 18
        for index in range(0, len(full_answer), chunk_size):
            yield {"type": "token", "text": full_answer[index : index + chunk_size]}

        final_result = PipelineResult(
            question=question,
            used_retrieval=True,
            answer=full_answer,
            evidence=evidence,
            debug={
                "encoder_type": self.encoder.__class__.__name__,
                "index_type": self.index.__class__.__name__,
                "raw_hits": [asdict(hit) for hit in hits],
                "top_hit_score": hits[0].score if hits else 0.0,
                "evidence_count": len(evidence),
            },
        )
        yield {"type": "done", "result": final_result.to_dict()}
