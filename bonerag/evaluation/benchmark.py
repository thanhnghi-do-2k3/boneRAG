"""Reproducible image-RAG benchmark protocol for the FracAtlas deployment.

The benchmark deliberately refuses the in-code toy corpus. It selects a fixed,
balanced set of real files from the mounted FracAtlas folders, excludes the
whole test hold-out from retrieval, and evaluates every system on the same cases.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from bonerag.main_algo.data import (
    ImageRecord,
    infer_diagnosis_from_image_path,
    resolve_dataset_image_path,
)
from bonerag.main_algo.pipeline import BoneRAGPipeline, PipelineResult


BENCHMARK_VERSION = "bonerag-fracatlas-image-v1"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    query_image_id: str
    query_image_path: str
    question: str
    expected_diagnosis: str
    expected_body_part: str
    source: str = "FracAtlas"


SYSTEMS: tuple[dict[str, Any], ...] = (
    {
        "key": "text_rag",
        "label": "Text-only RAG",
        "description": "Chỉ truy vấn text trên cùng corpus/index.",
        "use_image": False,
        "rerank": False,
    },
    {
        "key": "image_rag",
        "label": "Image-only RAG",
        "description": "Chỉ dùng embedding ảnh, không dùng reranking domain.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": False,
    },
    {
        "key": "multimodal_rag",
        "label": "Image + Text RAG",
        "description": "Blend 60% image + 40% text, không reranking domain.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": False,
    },
    {
        "key": "bonerag",
        "label": "BoneRAG (ours)",
        "description": "Image + text, anatomical/pathology reranking và gate.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": True,
    },
)


def _even_sample(records: list[ImageRecord], count: int) -> list[ImageRecord]:
    if len(records) <= count:
        return records
    # Deterministic evenly spaced sampling avoids a label/order-specific prefix.
    indexes = [round((idx + 0.5) * len(records) / count - 0.5) for idx in range(count)]
    return [records[index] for index in indexes]


def build_cases(records: list[ImageRecord], cases_per_label: int = 16) -> list[BenchmarkCase]:
    """Build a balanced, deterministic case set from actual image files."""
    by_label: dict[str, list[tuple[str, ImageRecord]]] = {"fracture": [], "normal": []}
    for record in records:
        resolved = resolve_dataset_image_path(record.image_path)
        label = infer_diagnosis_from_image_path(resolved or record.image_path)
        if label and resolved:
            by_label[label].append((str(resolved), record))

    if not by_label["fracture"] or not by_label["normal"]:
        raise RuntimeError(
            "Benchmark cần dataset FracAtlas thật gồm cả Fractured và Non_fractured. "
            "Không được chạy trên fallback corpus."
        )

    cases: list[BenchmarkCase] = []
    for label in ("fracture", "normal"):
        pairs = sorted(by_label[label], key=lambda pair: pair[0].lower())
        for index, (path, record) in enumerate(_even_sample(pairs, cases_per_label)):
            cases.append(
                BenchmarkCase(
                    case_id=f"{label}-{index + 1:03d}",
                    query_image_id=record.image_id,
                    query_image_path=path,
                    question="Does this X-ray show a bone fracture?",
                    expected_diagnosis=label,
                    expected_body_part=record.body_part,
                )
            )
    return cases


def dataset_fingerprint(cases: list[BenchmarkCase]) -> str:
    payload = "\n".join(
        f"{case.query_image_id}|{case.query_image_path}|{case.expected_diagnosis}"
        for case in cases
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _label_in_text(answer: str, expected: str) -> bool:
    normalized = answer.lower()
    if expected == "fracture":
        return any(term in normalized for term in ("fracture", "fractured", "gãy xương", "gãy"))
    return any(term in normalized for term in ("normal", "no fracture", "không gãy", "bình thường"))


def _run_one_case(
    pipeline: BoneRAGPipeline,
    case: BenchmarkCase,
    system: dict[str, Any],
    test_query_ids: set[str] | None = None,
) -> tuple[PipelineResult, float]:
    original_weights = (
        pipeline.reranker.weight_sim,
        pipeline.reranker.weight_anatomy,
        pipeline.reranker.weight_pathology,
        pipeline.reranker.hard_negative_penalty,
    )
    try:
        if not system["rerank"]:
            pipeline.reranker.weight_anatomy = 0.0
            pipeline.reranker.weight_pathology = 0.0
            pipeline.reranker.hard_negative_penalty = 0.0
        start = time.perf_counter()
        question = case.question
        if not system["use_image"]:
            # Keep the text-only baseline in-domain without leaking the label or
            # the query image id into the text encoder.
            question = f"{case.question}\n\nSelected image context: modality X-ray."
        events: Iterator[dict[str, object]] = pipeline.answer_events(
            question,
            image_input=case.query_image_path if system["use_image"] else None,
            exclude_ids=(test_query_ids or set()) | {case.query_image_id},
            image_alpha=system.get("image_alpha", 0.6),
        )
        result: PipelineResult | None = None
        for event in events:
            if event.get("type") == "done":
                result = PipelineResult(
                    question=event["result"]["question"],
                    used_retrieval=event["result"]["used_retrieval"],
                    answer=event["result"]["answer"],
                    evidence=[
                        _evidence_from_dict(item) for item in event["result"].get("evidence", [])
                    ],
                    debug=event["result"].get("debug", {}),
                )
                break
        if result is None:
            raise RuntimeError(f"Pipeline không phát event done cho {case.case_id}")
        return result, (time.perf_counter() - start) * 1000.0
    finally:
        (
            pipeline.reranker.weight_sim,
            pipeline.reranker.weight_anatomy,
            pipeline.reranker.weight_pathology,
            pipeline.reranker.hard_negative_penalty,
        ) = original_weights


def _evidence_from_dict(item: dict[str, Any]):
    from bonerag.main_algo.pipeline import Evidence

    fields = {field: item.get(field) for field in Evidence.__dataclass_fields__}
    fields["fracture_boxes"] = fields.get("fracture_boxes") or None
    return Evidence(**fields)


def score_case(case: BenchmarkCase, result: PipelineResult, latency_ms: float) -> dict[str, Any]:
    evidence = result.evidence[:4]
    top = evidence[0] if evidence else None
    expected = case.expected_diagnosis
    evidence_labels = [item.diagnosis for item in evidence]
    return {
        "case_id": case.case_id,
        "query_image_id": case.query_image_id,
        "expected_diagnosis": expected,
        "predicted_top_diagnosis": top.diagnosis if top else None,
        "retrieval_top1_label_accuracy": float(bool(top and top.diagnosis == expected)),
        "evidence_label_precision_at_4": (
            sum(label == expected for label in evidence_labels) / len(evidence_labels)
            if evidence_labels else 0.0
        ),
        "answer_label_accuracy": float(_label_in_text(result.answer, expected)),
        "used_retrieval": result.used_retrieval,
        "top_evidence_id": top.image_id if top else None,
        "top_score": top.rerank_score if top else 0.0,
        "latency_ms": round(latency_ms, 2),
        "answer": result.answer,
        "evidence_ids": [item.image_id for item in evidence],
    }


def run_system_case(
    pipeline: BoneRAGPipeline,
    case: BenchmarkCase,
    system: dict[str, Any],
    test_query_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Run one real case and return a serializable per-case result."""
    result, latency_ms = _run_one_case(pipeline, case, system, test_query_ids=test_query_ids)
    return {
        **score_case(case, result, latency_ms),
        "system_key": system["key"],
        "system_label": system["label"],
        "encoder": pipeline.encoder.__class__.__name__,
        "generator": pipeline.generator.name,
        "generator_fallback": bool(getattr(pipeline.generator, "fallback_used", False)),
    }


def aggregate_case_scores(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "retrieval_top1_label_accuracy",
        "evidence_label_precision_at_4",
        "answer_label_accuracy",
        "latency_ms",
    )
    summary: dict[str, Any] = {"n_cases": len(case_scores)}
    for key in keys:
        values = [float(item[key]) for item in case_scores]
        summary[key] = round(sum(values) / len(values), 4) if values else None
    fallback_values = [float(item.get("generator_fallback", False)) for item in case_scores]
    summary["generator_fallback_rate"] = (
        round(sum(fallback_values) / len(fallback_values), 4) if fallback_values else 0.0
    )
    return summary


def protocol_metadata(cases: list[BenchmarkCase]) -> dict[str, Any]:
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "dataset": "FracAtlas",
        "dataset_fingerprint": dataset_fingerprint(cases),
        "n_cases": len(cases),
        "cases_per_label": len(cases) // 2,
        "test_holdout": True,
        "test_ids_excluded_from_retrieval": True,
        "systems": [
            {key: value for key, value in system.items() if key != "description"}
            for system in SYSTEMS
        ],
    }
