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
from bonerag.main_algo.factuality import FactualityAuditor
from bonerag.main_algo.encoder import normalize
from bonerag.main_algo.pipeline import BoneRAGPipeline, PipelineResult
from bonerag.main_algo.vector_index import SearchHit, dot
from bonerag.evaluation.grounded_vqa_protocol import (
    build_grounded_vqa_manifest,
    scope_warnings,
)


BENCHMARK_VERSION = "bonerag-grounded-vqa-v5"
FACTUALITY_AUDITOR = FactualityAuditor()


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
    question_type: str = "decision_presence"
    answer_type: str = "closed_binary"
    expected_answer: str | None = None
    gold_source: str = "classification label"
    grounding_available: bool = False


PRIMARY_SYSTEMS: tuple[dict[str, Any], ...] = (
    {
        "key": "image_rag",
        "label": "Image-only RAG",
        "description": "Nearest-neighbor image retrieval baseline; top evidence drives the answer.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": False,
    },
    {
        "key": "zero_shot_prompt",
        "label": "Zero-shot Prompt Classifier",
        "description": "Deterministic classifier: compare query image embedding with fracture/normal text prompt prototypes.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": False,
        "classifier_mode": "zero_shot_prompt",
        "top_k": 4,
    },
    {
        "key": "knn_majority",
        "label": "kNN Majority Vote",
        "description": "Deterministic classifier: majority label among k nearest image embeddings.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": False,
        "classifier_mode": "knn_majority",
        "top_k": 5,
    },
    {
        "key": "knn_weighted",
        "label": "Similarity-weighted kNN",
        "description": "Deterministic classifier: similarity-weighted vote among k nearest image embeddings.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": False,
        "classifier_mode": "knn_weighted",
        "top_k": 5,
    },
    {
        "key": "centroid_classifier",
        "label": "Class-centroid Prototype",
        "description": "Deterministic classifier: compare query image embedding with fracture/normal class centroids.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": False,
        "classifier_mode": "centroid",
        "top_k": 4,
    },
    {
        "key": "bonerag",
        "label": "BoneRAG (ours)",
        "description": "Image retrieval với anatomical/pathology reranking và evidence gate.",
        "use_image": True,
        "image_alpha": 1.0,
        "rerank": True,
    },
)


ANSWER_ABLATION_SYSTEMS: tuple[dict[str, Any], ...] = (
    {
        "key": "bonerag_answer_calibrated",
        "label": "BoneRAG + Answer Calibration",
        "description": "BoneRAG retrieval giữ nguyên; chỉ thêm footer kết luận chuẩn hóa từ evidence để đo ảnh hưởng ở answer-level.",
        "use_image": True,
        "image_alpha": 1.0,
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
    # Kept for API/CLI compatibility. We do not run "paper-inspired" rows unless
    # the actual published method is reproduced on the same dataset and split.
    _ = include_literature_proxies
    systems = PRIMARY_SYSTEMS
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
                    expected_answer="yes" if label == "fracture" else "no",
                    grounding_available=bool(label == "fracture" and record.fracture_boxes),
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


def _majority_label(labels: list[str]) -> tuple[str | None, float]:
    valid = [label for label in labels if label in {"fracture", "normal"}]
    if not valid:
        return None, 0.0
    fracture_count = sum(label == "fracture" for label in valid)
    normal_count = sum(label == "normal" for label in valid)
    if fracture_count == normal_count:
        return None, fracture_count / len(valid)
    majority = "fracture" if fracture_count > normal_count else "normal"
    return majority, max(fracture_count, normal_count) / len(valid)


def _evidence_from_hit(pipeline: BoneRAGPipeline, hit: SearchHit):
    from bonerag.main_algo.pipeline import Evidence

    parent_id = hit.record_id.split("#")[0]
    rec = pipeline.record_by_id[parent_id]
    return Evidence(
        image_id=rec.image_id,
        image_path=rec.image_path,
        image_width=rec.image_width,
        image_height=rec.image_height,
        fracture_boxes=rec.fracture_boxes,
        title=rec.title,
        body_part=rec.body_part,
        diagnosis=rec.diagnosis,
        fracture_type=rec.fracture_type,
        region=rec.region,
        evidence_note=f"{rec.evidence_note} [Algorithm baseline evidence; no domain reranking.]",
        retrieval_score=hit.score,
        rerank_score=hit.score,
    )


def _plain_evidence_from_hits(pipeline: BoneRAGPipeline, hits: list[SearchHit]):
    return [
        _evidence_from_hit(pipeline, hit)
        for hit in hits
        if hit.record_id.split("#")[0] in pipeline.record_by_id
    ]


def _vote_prediction(evidence, weighted: bool = False) -> tuple[str | None, float, dict[str, float]]:
    weights: dict[str, float] = {"fracture": 0.0, "normal": 0.0}
    for index, item in enumerate(evidence):
        if item.diagnosis not in weights:
            continue
        weight = max(0.0, float(item.retrieval_score)) + 1e-6 if weighted else 1.0
        # Tiny rank bonus makes exact ties deterministic without changing normal cases.
        weight += 1e-9 * (len(evidence) - index)
        weights[item.diagnosis] += weight
    total = weights["fracture"] + weights["normal"]
    if total <= 0:
        return None, 0.0, weights
    if math.isclose(weights["fracture"], weights["normal"], abs_tol=1e-12):
        label = evidence[0].diagnosis if evidence and evidence[0].diagnosis in weights else None
    else:
        label = "fracture" if weights["fracture"] > weights["normal"] else "normal"
    confidence = weights[label] / total if label else 0.0
    return label, confidence, {key: round(value, 6) for key, value in weights.items()}


def _answer_from_algorithm(label: str | None, confidence: float, mode: str) -> str:
    _ = confidence, mode
    if label == "fracture":
        return "fracture"
    if label == "normal":
        return "normal"
    return "unknown"


def _vector_from_index(pipeline: BoneRAGPipeline, record_id: str):
    index = pipeline.index
    if hasattr(index, "_vectors"):
        vectors = getattr(index, "_vectors")
        vector = vectors.get(record_id) or vectors.get(f"{record_id}#image")
        if vector is not None:
            return tuple(float(value) for value in vector)
    if hasattr(index, "id_to_record") and hasattr(index, "index"):
        id_to_record = getattr(index, "id_to_record")
        try:
            position = id_to_record.index(record_id)
        except ValueError:
            position = -1
        if position >= 0:
            reconstructed = index.index.reconstruct(position)
            return tuple(float(value) for value in reconstructed.tolist())
    return None


def _record_vector(pipeline: BoneRAGPipeline, record: ImageRecord):
    vector = _vector_from_index(pipeline, record.image_id)
    if vector is not None:
        return vector
    if record.image_path and Path(record.image_path).exists():
        try:
            return pipeline.encoder.encode_image(record.image_path)
        except Exception:
            pass
    return pipeline.encoder.encode_text(record.text)


def _class_centroids(
    pipeline: BoneRAGPipeline,
    exclude_ids: set[str],
) -> dict[str, tuple[float, ...]]:
    cache = getattr(pipeline, "_benchmark_baseline_cache", None)
    if cache is None:
        cache = {}
        setattr(pipeline, "_benchmark_baseline_cache", cache)
    cache_key = ("class_centroids", tuple(sorted(exclude_ids)))
    if cache_key in cache:
        return cache[cache_key]

    vectors_by_label: dict[str, list[tuple[float, ...]]] = {"fracture": [], "normal": []}
    for record in pipeline.records:
        if record.image_id in exclude_ids or record.diagnosis not in vectors_by_label:
            continue
        vectors_by_label[record.diagnosis].append(_record_vector(pipeline, record))

    centroids: dict[str, tuple[float, ...]] = {}
    for label, vectors in vectors_by_label.items():
        if not vectors:
            continue
        dim = len(vectors[0])
        averaged = [
            sum(vector[idx] for vector in vectors if len(vector) == dim) / len(vectors)
            for idx in range(dim)
        ]
        centroids[label] = normalize(averaged)
    cache[cache_key] = centroids
    return centroids


def _prompt_prototypes(pipeline: BoneRAGPipeline) -> dict[str, tuple[float, ...]]:
    cache = getattr(pipeline, "_benchmark_baseline_cache", None)
    if cache is None:
        cache = {}
        setattr(pipeline, "_benchmark_baseline_cache", cache)
    cache_key = ("zero_shot_prompt_prototypes", pipeline.encoder.__class__.__name__)
    if cache_key in cache:
        return cache[cache_key]

    prompts = {
        "fracture": [
            "x-ray radiograph showing a bone fracture",
            "fractured bone x-ray with cortical break",
            "abnormal radiograph with visible fracture line",
            "medical xray positive for fracture",
        ],
        "normal": [
            "normal x-ray radiograph without bone fracture",
            "healthy bone x-ray with intact cortex",
            "medical xray negative for fracture",
            "no acute fracture on radiograph",
        ],
    }
    prototypes: dict[str, tuple[float, ...]] = {}
    for label, prompt_list in prompts.items():
        vectors = [pipeline.encoder.encode_text(prompt) for prompt in prompt_list]
        dim = len(vectors[0])
        averaged = [
            sum(vector[idx] for vector in vectors if len(vector) == dim) / len(vectors)
            for idx in range(dim)
        ]
        prototypes[label] = normalize(averaged)
    cache[cache_key] = prototypes
    return prototypes


def _zero_shot_prompt_prediction(
    pipeline: BoneRAGPipeline,
    case: BenchmarkCase,
) -> tuple[str | None, float, dict[str, float]]:
    query_vector = pipeline.encoder.encode_image(case.query_image_path)
    prototypes = _prompt_prototypes(pipeline)
    scores = {
        label: dot(query_vector, prototype)
        for label, prototype in prototypes.items()
        if len(query_vector) == len(prototype)
    }
    if not scores:
        return None, 0.0, {}
    label = max(scores, key=scores.get)
    sorted_scores = sorted(scores.values(), reverse=True)
    margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
    return label, max(0.0, float(margin)), {key: round(value, 6) for key, value in scores.items()}


def _centroid_prediction(
    pipeline: BoneRAGPipeline,
    case: BenchmarkCase,
    exclude_ids: set[str],
) -> tuple[str | None, float, dict[str, float]]:
    query_vector = pipeline.encoder.encode_image(case.query_image_path)
    centroids = _class_centroids(pipeline, exclude_ids)
    scores = {
        label: dot(query_vector, centroid)
        for label, centroid in centroids.items()
        if len(query_vector) == len(centroid)
    }
    if not scores:
        return None, 0.0, {}
    label = max(scores, key=scores.get)
    sorted_scores = sorted(scores.values(), reverse=True)
    margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]
    return label, max(0.0, float(margin)), {key: round(value, 6) for key, value in scores.items()}


def _run_classifier_case(
    pipeline: BoneRAGPipeline,
    case: BenchmarkCase,
    system: dict[str, Any],
    test_query_ids: set[str] | None = None,
) -> tuple[PipelineResult, float]:
    original_top_k = pipeline.top_k
    original_min_similarity = pipeline.min_similarity
    original_gate_min_similarity = pipeline.gate.min_similarity
    mode = str(system.get("classifier_mode"))
    exclude_ids = (test_query_ids or set()) | {case.query_image_id}
    try:
        pipeline.top_k = int(system.get("top_k", 5))
        start = time.perf_counter()
        hits = pipeline.retrieve(
            case.question,
            image_input=case.query_image_path,
            exclude_ids=exclude_ids,
            image_alpha=float(system.get("image_alpha", 1.0)),
        )
        evidence = _plain_evidence_from_hits(pipeline, hits)
        if mode == "zero_shot_prompt":
            label, confidence, scores = _zero_shot_prompt_prediction(pipeline, case)
        elif mode == "centroid":
            label, confidence, scores = _centroid_prediction(pipeline, case, exclude_ids)
        else:
            label, confidence, scores = _vote_prediction(evidence, weighted=(mode == "knn_weighted"))
        answer = _answer_from_algorithm(label, confidence, mode)
        result = PipelineResult(
            question=case.question,
            used_retrieval=True,
            answer=answer,
            evidence=evidence,
            debug={
                "classifier_mode": mode,
                "classifier_prediction": label,
                "classifier_confidence": round(confidence, 4),
                "classifier_scores": scores,
                "encoder_type": pipeline.encoder.__class__.__name__,
                "generator_type": "deterministic_algorithm",
                "index_type": pipeline.index.__class__.__name__,
                "top_hit_score": hits[0].score if hits else 0.0,
                "evidence_count": len(evidence),
            },
        )
        return result, (time.perf_counter() - start) * 1000.0
    finally:
        pipeline.top_k = original_top_k
        pipeline.min_similarity = original_min_similarity
        pipeline.gate.min_similarity = original_gate_min_similarity


def _run_one_case(
    pipeline: BoneRAGPipeline,
    case: BenchmarkCase,
    system: dict[str, Any],
    test_query_ids: set[str] | None = None,
) -> tuple[PipelineResult, float]:
    if system.get("classifier_mode"):
        return _run_classifier_case(pipeline, case, system, test_query_ids=test_query_ids)

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
    evidence_majority, evidence_consensus = _majority_label(evidence_labels)
    answer_label = _diagnosis_from_text(result.answer)
    classifier_label = result.debug.get("classifier_prediction")
    decision_label = classifier_label or answer_label or evidence_majority or (top.diagnosis if top else None)
    decision_source = (
        "classifier"
        if classifier_label
        else "answer"
        if answer_label
        else "evidence_majority"
        if evidence_majority
        else "top_evidence"
        if top
        else "none"
    )
    decision_confidence = result.debug.get("classifier_confidence")
    if decision_confidence is None:
        decision_confidence = evidence_consensus if evidence_consensus else (top.rerank_score if top else 0.0)
    factuality = FACTUALITY_AUDITOR.audit(result.answer, evidence)
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
        "dataset": case.source,
        "question_type": case.question_type,
        "answer_type": case.answer_type,
        "gold_source": case.gold_source,
        "expected_answer": case.expected_answer,
        "expected_diagnosis": expected,
        "expected_body_part": case.expected_body_part,
        "grounding_available": case.grounding_available,
        "grounding_scored": False,
        "grounding_status": (
            "reference_available_not_scored_no_query_region_output"
            if case.grounding_available
            else "no_query_grounding_reference_for_this_case"
        ),
        "predicted_top_diagnosis": top.diagnosis if top else None,
        "evidence_majority_diagnosis": evidence_majority,
        "evidence_label_consensus": round(evidence_consensus, 4),
        "answer_predicted_diagnosis": answer_label,
        "classifier_predicted_diagnosis": classifier_label,
        "classifier_confidence": result.debug.get("classifier_confidence"),
        "classifier_scores": result.debug.get("classifier_scores"),
        "decision_predicted_diagnosis": decision_label,
        "decision_source": decision_source,
        "decision_confidence": round(float(decision_confidence), 4) if decision_confidence is not None else 0.0,
        "decision_label_accuracy": float(decision_label == expected),
        "retrieval_top1_label_accuracy": float(bool(top and top.diagnosis == expected)),
        "evidence_label_precision_at_4": (
            sum(label == expected for label in evidence_labels) / len(evidence_labels)
            if evidence_labels else 0.0
        ),
        "evidence_label_recall_at_4": float(any(label == expected for label in evidence_labels)),
        "evidence_label_mrr": round(1.0 / first_correct_rank, 4) if first_correct_rank else 0.0,
        "evidence_label_ndcg_at_4": round(dcg / idcg, 4) if idcg else 0.0,
        "answer_label_accuracy": float(answer_label == expected),
        "answer_matches_top_evidence": float(bool(answer_label and top and answer_label == top.diagnosis)),
        "answer_matches_evidence_majority": float(bool(answer_label and evidence_majority and answer_label == evidence_majority)),
        "answer_factuality_score": factuality.score,
        "answer_supported_claims": factuality.supported_claims,
        "answer_unsupported_claims": factuality.unsupported_claims,
        "answer_hallucination_warning": factuality.has_hallucination_warning,
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
        "decision_label_accuracy",
        "decision_confidence",
        "retrieval_top1_label_accuracy",
        "evidence_label_precision_at_4",
        "evidence_label_recall_at_4",
        "evidence_label_mrr",
        "evidence_label_ndcg_at_4",
        "evidence_label_consensus",
        "answer_label_accuracy",
        "answer_matches_top_evidence",
        "answer_matches_evidence_majority",
        "answer_factuality_score",
        "latency_ms",
    )
    summary: dict[str, Any] = {"n_cases": len(case_scores)}
    for key in keys:
        values = [float(item.get(key, 0.0)) for item in case_scores]
        summary[key] = round(sum(values) / len(values), 4) if values else None
    fallback_values = [float(item.get("generator_fallback", False)) for item in case_scores]
    summary["generator_fallback_rate"] = (
        round(sum(fallback_values) / len(fallback_values), 4) if fallback_values else 0.0
    )
    warning_values = [float(item.get("answer_hallucination_warning", False)) for item in case_scores]
    summary["answer_hallucination_warning_rate"] = (
        round(sum(warning_values) / len(warning_values), 4) if warning_values else 0.0
    )
    summary["answer_supported_claims"] = sum(int(item.get("answer_supported_claims", 0)) for item in case_scores)
    summary["answer_unsupported_claims"] = sum(int(item.get("answer_unsupported_claims", 0)) for item in case_scores)
    summary["grounding_evaluable_cases"] = sum(1 for item in case_scores if item.get("grounding_available"))
    summary["grounding_scored"] = False
    summary.update(_classification_metrics(case_scores, "predicted_top_diagnosis", "retrieval"))
    summary.update(_classification_metrics(case_scores, "answer_predicted_diagnosis", "answer"))
    summary.update(_classification_metrics(case_scores, "decision_predicted_diagnosis", "decision"))
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
    grounded_vqa = build_grounded_vqa_manifest(active_dataset_key="fracatlas")
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "dataset": "FracAtlas",
        "task": "FracAtlas-derived closed fracture grounded VQA pilot",
        "paper_safe_task_name": grounded_vqa["paper_safe_task_name"],
        "vqa_task_scope": "label-derived closed-ended VQA from FracAtlas annotations",
        "native_vqa_dataset": False,
        "dataset_fingerprint": dataset_fingerprint(cases),
        "n_cases": len(cases),
        "cases_per_label": len(cases) // 2,
        "test_holdout": True,
        "test_ids_excluded_from_retrieval": True,
        "external_text_corpus": False,
        "official_paper_reproductions": False,
        "vqa_explanation_ground_truth": False,
        "query_localization_output_scored": False,
        "grounding_reference_cases": sum(1 for case in cases if case.grounding_available),
        "grounded_vqa_manifest": grounded_vqa,
        "scope_warnings": scope_warnings(grounded_vqa),
        "systems": [
            {key: value for key, value in system.items() if key != "description"}
            for system in systems
        ],
    }
