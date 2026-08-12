"""Reproducible image-RAG benchmark protocol for the FracAtlas deployment.

The benchmark deliberately refuses the in-code toy corpus. It selects a fixed,
balanced set of real files from the mounted FracAtlas folders, excludes the
whole test hold-out from retrieval, and evaluates every system on the same cases.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
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


BENCHMARK_VERSION = "bonerag-fracatlas-image-v2"


def benchmark_runs_path() -> Path:
    runtime_dir = os.environ.get("BONERAG_RUNTIME_DATA_DIR", "").strip()
    path = (
        Path(runtime_dir).expanduser() / "benchmark_runs.jsonl"
        if runtime_dir
        else Path(__file__).resolve().parent / "benchmark_runs.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    query_image_id: str
    query_image_path: str
    question: str
    expected_diagnosis: str
    expected_body_part: str
    source: str = "FracAtlas"


PRIMARY_SYSTEMS: tuple[dict[str, Any], ...] = (
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
        "label": "Image + Metadata RAG",
        "description": "Blend 60% image + 40% metadata/query text, không dùng external text corpus.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": False,
    },
    {
        "key": "bonerag",
        "label": "BoneRAG (ours)",
        "description": "Image + metadata/query text, anatomical/pathology reranking và evidence gate.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": True,
    },
)


LITERATURE_PROXY_SYSTEMS: tuple[dict[str, Any], ...] = (
    {
        "key": "mmedrag_adaptive_context_proxy",
        "label": "MMed-RAG-inspired Adaptive Context",
        "description": "Exploratory proxy: image+metadata với top-k context lớn hơn để kiểm tra adaptive-context. Không phải reproduction chính thức của MMed-RAG.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": False,
        "top_k": 6,
        "paper_reference": "MMed-RAG-inspired proxy, not official reproduction",
    },
    {
        "key": "factmm_rerank_proxy",
        "label": "FactMM-RAG-inspired Fact Rerank",
        "description": "Exploratory proxy: rerank nhẹ theo anatomy/pathology để kiểm tra fact-aware evidence ordering. Không phải reproduction chính thức của FactMM-RAG.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": True,
        "reranker_weights": {
            "weight_sim": 0.65,
            "weight_anatomy": 0.25,
            "weight_pathology": 0.10,
            "hard_negative_penalty": 0.15,
        },
        "paper_reference": "FactMM-RAG-inspired proxy, not official reproduction",
    },
    {
        "key": "rule_gated_proxy",
        "label": "RULE-inspired Gated RAG",
        "description": "Exploratory proxy: image+metadata với evidence gate nghiêm hơn để kiểm tra reliability/safety. Không phải reproduction chính thức của RULE.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": False,
        "min_similarity": 0.08,
        "paper_reference": "RULE-inspired proxy, not official reproduction",
    },
)


ANSWER_ABLATION_SYSTEMS: tuple[dict[str, Any], ...] = (
    {
        "key": "bonerag_answer_calibrated",
        "label": "BoneRAG + Answer Calibration",
        "description": "BoneRAG retrieval giữ nguyên; chỉ thêm footer kết luận chuẩn hóa từ evidence để đo ảnh hưởng ở answer-level.",
        "use_image": True,
        "image_alpha": 0.6,
        "rerank": True,
        "answer_calibration": True,
    },
)


SYSTEMS: tuple[dict[str, Any], ...] = PRIMARY_SYSTEMS


def benchmark_systems(
    include_controls: bool = False,
    include_literature_proxies: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Return the publishable default systems, optionally with audit-only rows."""
    systems = PRIMARY_SYSTEMS
    if include_literature_proxies:
        systems = systems + LITERATURE_PROXY_SYSTEMS
    if include_controls:
        systems = systems + ANSWER_ABLATION_SYSTEMS
    return systems


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


def _diagnosis_from_text(answer: str) -> str | None:
    """Map a generated answer to the benchmark's binary label space."""
    normalized = answer.lower()
    calibrated = re.search(r"kết luận chuẩn hóa bonerag:\s*(fracture|normal)\b", normalized)
    if calibrated:
        return calibrated.group(1)

    normal_patterns = (
        r"\bnormal\b",
        r"\bno\s+(?:acute\s+)?fracture\b",
        r"\bwithout\s+(?:a\s+)?fracture\b",
        r"không\s+(?:có\s+)?(?:bằng chứng\s+)?(?:gãy|fracture|骨折)",
        r"không\s+(?:thấy|phát hiện).*?(?:gãy|fracture|骨折)",
        r"bình thường",
    )
    if any(re.search(pattern, normalized) for pattern in normal_patterns):
        return "normal"

    fracture_patterns = (
        r"\bfracture\b",
        r"\bfractured\b",
        r"\bbroken\b",
        r"gãy xương",
        r"\bgãy\b",
        r"骨折",
    )
    if any(re.search(pattern, normalized) for pattern in fracture_patterns):
        return "fracture"
    return None


def _label_in_text(answer: str, expected: str) -> bool:
    return _diagnosis_from_text(answer) == expected


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
    original_top_k = pipeline.top_k
    original_min_similarity = pipeline.min_similarity
    original_gate_min_similarity = pipeline.gate.min_similarity
    original_label_consensus = pipeline.enable_label_consensus_rerank
    original_answer_calibration = pipeline.enable_answer_calibration
    try:
        pipeline.enable_label_consensus_rerank = bool(system.get("label_consensus", False))
        pipeline.enable_answer_calibration = bool(system.get("answer_calibration", False))
        if "top_k" in system:
            pipeline.top_k = int(system["top_k"])
        if "min_similarity" in system:
            pipeline.min_similarity = float(system["min_similarity"])
            pipeline.gate.min_similarity = float(system["min_similarity"])
        if not system["rerank"]:
            pipeline.reranker.weight_anatomy = 0.0
            pipeline.reranker.weight_pathology = 0.0
            pipeline.reranker.hard_negative_penalty = 0.0
        elif system.get("reranker_weights"):
            weights = system["reranker_weights"]
            pipeline.reranker.weight_sim = float(weights.get("weight_sim", pipeline.reranker.weight_sim))
            pipeline.reranker.weight_anatomy = float(weights.get("weight_anatomy", pipeline.reranker.weight_anatomy))
            pipeline.reranker.weight_pathology = float(weights.get("weight_pathology", pipeline.reranker.weight_pathology))
            pipeline.reranker.hard_negative_penalty = float(weights.get("hard_negative_penalty", pipeline.reranker.hard_negative_penalty))
        start = time.perf_counter()
        question = case.question
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
        pipeline.top_k = original_top_k
        pipeline.min_similarity = original_min_similarity
        pipeline.gate.min_similarity = original_gate_min_similarity
        pipeline.enable_label_consensus_rerank = original_label_consensus
        pipeline.enable_answer_calibration = original_answer_calibration


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
    first_correct_rank = next(
        (index for index, label in enumerate(evidence_labels, start=1) if label == expected),
        None,
    )
    dcg = sum(
        (1.0 if label == expected else 0.0) / (1 if rank == 1 else math.log2(rank + 1))
        for rank, label in enumerate(evidence_labels, start=1)
    )
    ideal_correct = min(len([label for label in evidence_labels if label == expected]), 4)
    idcg = sum(1.0 / (1 if rank == 1 else math.log2(rank + 1)) for rank in range(1, ideal_correct + 1))
    return {
        "case_id": case.case_id,
        "query_image_id": case.query_image_id,
        "expected_diagnosis": expected,
        "predicted_top_diagnosis": top.diagnosis if top else None,
        "answer_predicted_diagnosis": _diagnosis_from_text(result.answer),
        "retrieval_top1_label_accuracy": float(bool(top and top.diagnosis == expected)),
        "evidence_label_precision_at_4": (
            sum(label == expected for label in evidence_labels) / len(evidence_labels)
            if evidence_labels else 0.0
        ),
        "evidence_label_recall_at_4": float(any(label == expected for label in evidence_labels)),
        "evidence_label_mrr": round(1.0 / first_correct_rank, 4) if first_correct_rank else 0.0,
        "evidence_label_ndcg_at_4": round(dcg / idcg, 4) if idcg else 0.0,
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
        "paper_reference": system.get("paper_reference"),
        "encoder": pipeline.encoder.__class__.__name__,
        "generator": pipeline.generator.name,
        "generator_fallback": bool(getattr(pipeline.generator, "fallback_used", False)),
    }


def aggregate_case_scores(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "retrieval_top1_label_accuracy",
        "evidence_label_precision_at_4",
        "evidence_label_recall_at_4",
        "evidence_label_mrr",
        "evidence_label_ndcg_at_4",
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
    summary.update(_classification_metrics(case_scores, "predicted_top_diagnosis", "retrieval"))
    summary.update(_classification_metrics(case_scores, "answer_predicted_diagnosis", "answer"))
    return summary


def _classification_metrics(
    case_scores: list[dict[str, Any]],
    prediction_key: str,
    prefix: str,
) -> dict[str, Any]:
    """Compute fracture-positive binary classification metrics."""
    tp = tn = fp = fn = unknown = 0
    positives = negatives = 0
    for item in case_scores:
        expected = item.get("expected_diagnosis")
        predicted = item.get(prediction_key)
        if expected == "fracture":
            positives += 1
            if predicted == "fracture":
                tp += 1
            elif predicted == "normal":
                fn += 1
            else:
                unknown += 1
                fn += 1
        elif expected == "normal":
            negatives += 1
            if predicted == "normal":
                tn += 1
            elif predicted == "fracture":
                fp += 1
            else:
                unknown += 1
                fp += 1

    sensitivity = tp / positives if positives else 0.0
    specificity = tn / negatives if negatives else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = sensitivity
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    balanced_accuracy = (sensitivity + specificity) / 2 if case_scores else 0.0

    return {
        f"{prefix}_tp": tp,
        f"{prefix}_tn": tn,
        f"{prefix}_fp": fp,
        f"{prefix}_fn": fn,
        f"{prefix}_unknown": unknown,
        f"{prefix}_sensitivity": round(sensitivity, 4),
        f"{prefix}_specificity": round(specificity, 4),
        f"{prefix}_precision": round(precision, 4),
        f"{prefix}_f1": round(f1, 4),
        f"{prefix}_balanced_accuracy": round(balanced_accuracy, 4),
    }


def protocol_metadata(cases: list[BenchmarkCase], systems: tuple[dict[str, Any], ...] = SYSTEMS) -> dict[str, Any]:
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
            for system in systems
        ],
    }
