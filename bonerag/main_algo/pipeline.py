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

from .citation_synthesizer import EvidenceCitationSynthesizer
from .data import (
    ImageRecord,
    SAMPLE_RECORDS,
    infer_diagnosis_from_image_path,
    resolve_dataset_image_path,
)
from .encoder import BaseMultimodalEncoder, get_multimodal_encoder
from .factuality import FactualityAuditor
from .gating import EvidenceGate, GateDecision
from .generator import AVAILABLE_GENERATORS, BaseGenerator, TemplateGenerator, get_generator
from .reranker import AnatomicalReranker
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
        index_path: Path | str | None = None,
        metadata_path: Path | str | None = None,
    ) -> None:
        self.index_path = Path(index_path) if index_path else None
        self.metadata_path = Path(metadata_path) if metadata_path else None
        self.encoder = encoder or get_multimodal_encoder(mode="biomedclip")
        self.generator = generator or TemplateGenerator()
        self.top_k = top_k
        self.min_similarity = min_similarity

        # Load custom dataset metadata if provided
        if self.metadata_path and self.metadata_path.exists():
            import json
            with self.metadata_path.open("r", encoding="utf-8") as fh:
                meta_list = json.load(fh)
            loaded_records = []
            for item in meta_list:
                raw_image_path = item.get("image_path")
                resolved_image_path = resolve_dataset_image_path(raw_image_path)
                actual_diagnosis = infer_diagnosis_from_image_path(resolved_image_path or raw_image_path)
                diagnosis = actual_diagnosis or item.get("diagnosis", "unknown")
                raw_image_id = str(item.get("image_id", "")).strip()
                image_stem = Path(raw_image_path or raw_image_id).stem.lower()
                image_id = (
                    f"fracatlas-{diagnosis if diagnosis in {'fracture', 'normal'} else 'unknown'}-{image_stem}"
                    if image_stem
                    else raw_image_id
                )
                loaded_records.append(
                    ImageRecord(
                        image_id=image_id,
                        title=item.get("title", ""),
                        body_part=item.get("body_part", "unknown"),
                        diagnosis=diagnosis,
                        fracture_type="fractured" if diagnosis == "fracture" else "none" if diagnosis == "normal" else item.get("fracture_type", "unknown"),
                        region=item.get("region", "unknown"),
                        evidence_note=item.get("evidence_note", ""),
                        text=item.get("text", ""),
                        image_path=str(resolved_image_path) if resolved_image_path else raw_image_path,
                    )
                )
            self.records = loaded_records
        else:
            from bonerag.main_algo.data import get_sample_records
            self.records = records or get_sample_records()

        self.record_by_id = {record.image_id: record for record in self.records}
        self.reranker = AnatomicalReranker()
        self.gate = EvidenceGate(min_similarity=self.min_similarity)
        self.citation_formatter = EvidenceCitationSynthesizer()
        self.factuality_auditor = FactualityAuditor()
        self.index = self._build_index()

    def _build_index(self) -> InMemoryVectorIndex | FAISSVectorIndex:
        """Off-line phase: multi-level indexing or load pre-computed .faiss file."""

        dim = getattr(self.encoder, "dim", 512)

        # 1. Fast load from pre-computed FAISS index file on disk (<0.02s)
        if self.index_path and self.index_path.exists():
            try:
                from .vector_index import FAISSVectorIndex
                idx = FAISSVectorIndex(dim=dim)
                id_list = [r.image_id for r in self.records]
                idx.load_from_file(self.index_path, id_list)
                return idx
            except Exception as exc:
                print(f"[pipeline] Load index warning: {exc}, building in-memory...")

        # 2. Build on-the-fly if no pre-computed index file exists
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

    def retrieve(
        self,
        question: str,
        image_data_url: str | None = None,
        image_input: str | Path | None = None,
        exclude_ids: set[str] | None = None,
        image_alpha: float = 0.6,
    ) -> list[SearchHit]:
        """Online retrieval: encode query (text + optional image) and search index.

        Supports both user-pasted base64 images (image_data_url) and existing
        dataset image files on disk (image_input). The query vector is a weighted
        blend of text embedding (40%) and image embedding (60%) for multimodal RAG.
        """
        text_vec = self.encoder.encode_text(question)

        img_vec = None
        if image_input and Path(image_input).exists():
            try:
                img_vec = self.encoder.encode_image(image_input)
            except Exception:
                pass
        elif image_data_url:
            try:
                img_vec = self.encoder.encode_image_from_base64(image_data_url)
            except Exception:
                pass

        if img_vec:
            alpha = max(0.0, min(1.0, image_alpha))
            query_vector = tuple(
                (1 - alpha) * t + alpha * i
                for t, i in zip(text_vec, img_vec)
            )
            from .encoder import normalize
            query_vector = normalize(list(query_vector))
        else:
            query_vector = text_vec

        raw_hits = self.index.search(query_vector, top_k=self.top_k * 3)

        # Merge hits by parent record_id
        best_hits_by_parent: dict[str, tuple[float, str]] = {}
        for hit in raw_hits:
            parts = hit.record_id.split("#")
            parent_id = parts[0]
            match_type = parts[1] if len(parts) > 1 else "text_metadata"

            if parent_id not in self.record_by_id:
                continue
            if exclude_ids and parent_id in exclude_ids:
                continue

            if parent_id not in best_hits_by_parent or hit.score > best_hits_by_parent[parent_id][0]:
                best_hits_by_parent[parent_id] = (hit.score, match_type)

        merged_hits = [
            SearchHit(record_id=parent_id, score=score)
            for parent_id, (score, _) in best_hits_by_parent.items()
        ]
        merged_hits.sort(key=lambda item: item.score, reverse=True)
        return merged_hits[: self.top_k]

    def should_retrieve(self, question: str, hits: list[SearchHit], has_image: bool = False) -> bool:
        """Gate delta: evaluate adaptive evidence gating decision."""
        decision = self.gate.evaluate_hits(question, hits, has_image=has_image)
        return decision.passed

    def rerank(self, question: str, hits: list[SearchHit]) -> list[Evidence]:
        """Anatomical & Pathology Cross-Attribute Reranking with Hard Negative Mining."""
        return self.reranker.rerank_records(question, hits, self.record_by_id, top_k=self.top_k)

    def generate_answer(self, question: str, evidence: list[Evidence], used_retrieval: bool) -> str:
        """Call answer generator layer and attach structured evidence citations."""
        raw_answer = self.generator.generate(question, evidence, used_retrieval=used_retrieval)
        if not used_retrieval or not evidence:
            return raw_answer
        return self.citation_formatter.attach_inline_citations(raw_answer, evidence)

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

    def answer_events(
        self,
        question: str,
        image_data_url: str | None = None,
        image_input: str | Path | None = None,
        exclude_ids: set[str] | None = None,
        image_alpha: float = 0.6,
    ) -> Iterator[dict[str, object]]:
        """Alias for stream_answer used by HTTP server."""
        return self.stream_answer(
            question,
            image_data_url=image_data_url,
            image_input=image_input,
            exclude_ids=exclude_ids,
            image_alpha=image_alpha,
        )

    def stream_answer(
        self,
        question: str,
        image_data_url: str | None = None,
        image_input: str | Path | None = None,
        exclude_ids: set[str] | None = None,
        image_alpha: float = 0.6,
    ) -> Iterator[dict[str, object]]:
        """Stream pipeline stages over Server-Sent Events.

        Args:
            question: The (pipeline-enriched) question string.
            image_data_url: Optional base64 data URL of user-pasted image.
            image_input: Optional file path of selected library image.
        """
        has_image = bool(image_data_url or image_input)
        query_mode = "image+text" if has_image else "text-only"

        yield {"type": "stage", "stage": "receive-question", "message": f"Nhận câu hỏi: {question}"}
        yield {
            "type": "stage",
            "stage": "encode-question",
            "message": (
                f"Mã hóa [{query_mode}] bằng {self.encoder.__class__.__name__} → "
                f"vector {getattr(self.encoder, 'dim', 512)}-dim"
                + (" (ảnh đính kèm → blend 60% image + 40% text)" if has_image else "")
            ),
            "encoder": self.encoder.__class__.__name__,
            "query_mode": query_mode,
        }

        hits = self.retrieve(
            question,
            image_data_url=image_data_url,
            image_input=image_input,
            exclude_ids=exclude_ids,
            image_alpha=image_alpha,
        )
        yield {
            "type": "stage",
            "stage": "retrieve-hits",
            "message": f"Truy xuất được {len(hits)} ứng viên từ {self.index.__class__.__name__} (mode={query_mode})",
            "hits": [asdict(hit) for hit in hits],
        }

        used = self.should_retrieve(question, hits, has_image=has_image)
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
                    "generator_type": self.generator.name,
                    "index_type": self.index.__class__.__name__,
                    "query_mode": query_mode,
                    "raw_hits": [asdict(hit) for hit in hits],
                    "top_hit_score": hits[0].score if hits else 0.0,
                    "evidence_count": 0,
                    "model_config": {
                        "encoder": self.encoder.__class__.__name__,
                        "generator": self.generator.name,
                        "top_k": self.top_k,
                        "min_similarity": self.min_similarity,
                    },
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

        if hasattr(self.generator, "generate_stream"):
            token_list = []
            for token in self.generator.generate_stream(question, evidence, used_retrieval=True):
                token_list.append(token)
                yield {"type": "token", "text": token}
            full_answer = "".join(token_list)
        else:
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
                "generator_type": self.generator.name,
                "index_type": self.index.__class__.__name__,
                "query_mode": query_mode,
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
        yield {"type": "done", "result": final_result.to_dict()}
