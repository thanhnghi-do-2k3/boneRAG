"""Grounded VQA protocol manifest for bone pathology evaluation.

The project datasets named in the assignment are mostly annotation datasets,
not native VQA datasets. This module makes that distinction explicit in every
benchmark artifact so downstream reports do not overclaim.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


GROUNDED_VQA_PROTOCOL_VERSION = "bone-grounded-vqa-v1"


DATASET_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "key": "fracatlas",
        "label": "FracAtlas",
        "role": "core_bone_dataset",
        "status": "implemented_current_run",
        "native_vqa": False,
        "domain": "bone fracture radiographs",
        "source_annotations": ["classification label", "fracture boxes/masks when available"],
        "vqa_usage": "label-derived closed-ended fracture QA plus evidence retrieval audit",
        "implemented_metrics": ["decision", "evidence_retrieval", "answer_label_proxy"],
        "pending_metrics": ["query_lesion_grounding_iou", "radiologist_rationale_quality"],
    },
    {
        "key": "btxrd",
        "label": "BTXRD/BTRXD",
        "role": "planned_core_bone_dataset",
        "status": "loader_pending",
        "native_vqa": False,
        "domain": "primary bone tumor radiographs",
        "source_annotations": [
            "normal/tumor label",
            "benign/malignant label",
            "tumor boxes/masks",
            "clinical metadata",
        ],
        "vqa_usage": "label-derived tumor presence, benign/malignant, and lesion grounding QA",
        "implemented_metrics": [],
        "pending_metrics": ["decision", "subtype_macro_f1", "grounding_iou_or_dice", "evidence_retrieval"],
    },
    {
        "key": "grazpedwri_dx",
        "label": "GRAZPEDWRI-DX",
        "role": "planned_external_bone_dataset",
        "status": "loader_pending",
        "native_vqa": False,
        "domain": "pediatric wrist trauma radiographs",
        "source_annotations": ["image tags", "object boxes", "polygons", "AO fracture classes"],
        "vqa_usage": "annotation-derived wrist fracture/pathology QA and hard-negative grounding",
        "implemented_metrics": [],
        "pending_metrics": ["tag_accuracy", "detection_map", "grounding_iou", "evidence_retrieval"],
    },
    {
        "key": "radbench",
        "label": "RadBench",
        "role": "planned_external_vqa_benchmark",
        "status": "external_eval_pending",
        "native_vqa": True,
        "domain": "plain-film radiology VQA",
        "source_annotations": ["clinician-curated questions", "reference answers", "answer options"],
        "vqa_usage": "external sanity check for real radiology QA behavior, including fracture-style questions",
        "implemented_metrics": [],
        "pending_metrics": ["closed_accuracy", "open_answer_score", "multi_turn_case_accuracy"],
    },
    {
        "key": "imageclef_vqa_med_msk",
        "label": "ImageCLEF VQA-Med musculoskeletal subset",
        "role": "planned_external_vqa_benchmark",
        "status": "external_eval_pending",
        "native_vqa": True,
        "domain": "radiology VQA with musculoskeletal cases",
        "source_annotations": ["question-answer pairs", "modality/plane/organ/abnormality categories"],
        "vqa_usage": "external VQA subset for bone/spine/fracture/tumor questions",
        "implemented_metrics": [],
        "pending_metrics": ["exact_accuracy", "normalized_accuracy", "question_type_breakdown"],
    },
)


TASK_TAXONOMY: tuple[dict[str, Any], ...] = (
    {
        "key": "decision_presence",
        "label": "Disease presence decision",
        "question_examples": [
            "Does this X-ray show a bone fracture?",
            "Is there a bone tumor in this radiograph?",
        ],
        "answer_type": "closed",
        "gold_source": "classification label",
        "metrics": ["accuracy", "balanced_accuracy", "sensitivity", "specificity", "macro_f1"],
        "status": "implemented_for_fracatlas_fracture",
    },
    {
        "key": "decision_subtype",
        "label": "Pathology subtype decision",
        "question_examples": ["Is the tumor benign or malignant?"],
        "answer_type": "closed_multiclass",
        "gold_source": "subtype label",
        "metrics": ["macro_f1", "balanced_accuracy", "per_class_recall"],
        "status": "pending_btxrd_loader",
    },
    {
        "key": "lesion_grounding",
        "label": "Lesion grounding",
        "question_examples": ["Where is the suspected fracture or tumor region?"],
        "answer_type": "structured_region",
        "gold_source": "box or mask annotation",
        "metrics": ["IoU@0.5", "mAP@0.5", "Dice", "pointing_game_hit"],
        "status": "pending_model_region_output",
    },
    {
        "key": "evidence_retrieval",
        "label": "Visual evidence retrieval",
        "question_examples": ["Which similar cases support the answer?"],
        "answer_type": "ranked_evidence",
        "gold_source": "label/anatomy/pathology relevance policy",
        "metrics": ["Precision@k", "Recall@k", "MRR", "nDCG@k"],
        "status": "implemented_label_level_for_fracatlas",
    },
    {
        "key": "explanation_faithfulness",
        "label": "Explanation faithfulness",
        "question_examples": ["Why does the system think this image is abnormal?"],
        "answer_type": "free_text_plus_citations",
        "gold_source": "facts extracted from annotations and retrieved evidence",
        "metrics": ["fact_precision", "fact_recall", "hallucination_rate"],
        "status": "heuristic_only_until_reference_rationales_or_structured_facts",
    },
    {
        "key": "external_clinical_vqa",
        "label": "External clinician/radiology VQA",
        "question_examples": ["RadBench/ImageCLEF style real QA pairs"],
        "answer_type": "closed_and_open",
        "gold_source": "dataset reference answer",
        "metrics": ["closed_accuracy", "normalized_exact_match", "manual_or_llm_rubric_score"],
        "status": "pending_external_dataset_loader",
    },
)


BASELINE_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "key": "zero_shot_prompt",
        "label": "Zero-shot prompt classifier",
        "comparison_role": "foundation-model diagnostic baseline",
        "implemented": True,
    },
    {
        "key": "knn_majority",
        "label": "kNN majority vote",
        "comparison_role": "non-parametric image embedding baseline",
        "implemented": True,
    },
    {
        "key": "knn_weighted",
        "label": "Similarity-weighted kNN",
        "comparison_role": "weighted image retrieval classifier",
        "implemented": True,
    },
    {
        "key": "centroid_classifier",
        "label": "Class-centroid prototype",
        "comparison_role": "prototype/linear-like embedding baseline",
        "implemented": True,
    },
    {
        "key": "linear_probe",
        "label": "Frozen-embedding linear probe",
        "comparison_role": "supervised same-task classifier trained outside the test hold-out",
        "implemented": True,
    },
    {
        "key": "detector_segmenter",
        "label": "Detector/segmenter baseline",
        "comparison_role": "localization/segmentation baseline for boxed or masked datasets",
        "implemented": False,
    },
    {
        "key": "external_lmm",
        "label": "External LMM zero-shot/few-shot",
        "comparison_role": "foundation-model VQA baseline",
        "implemented": False,
    },
)


def build_grounded_vqa_manifest(active_dataset_key: str = "fracatlas") -> dict[str, Any]:
    """Return a JSON-safe manifest describing the benchmark scope."""
    datasets = deepcopy(list(DATASET_REGISTRY))
    tasks = deepcopy(list(TASK_TAXONOMY))
    baselines = deepcopy(list(BASELINE_REGISTRY))
    active = next((item for item in datasets if item["key"] == active_dataset_key), None)
    return {
        "schema_version": GROUNDED_VQA_PROTOCOL_VERSION,
        "active_dataset_key": active_dataset_key,
        "active_dataset": active,
        "paper_safe_task_name": "label-derived grounded VQA for bone pathology",
        "current_stage": (
            "FracAtlas-derived closed fracture QA pilot; external/native VQA and "
            "query-region grounding are not implemented in the current run."
        ),
        "datasets": datasets,
        "task_taxonomy": tasks,
        "baselines": baselines,
        "blocked_claims": [
            "open-ended clinician-authored bone VQA benchmark",
            "clinical diagnosis system",
            "superiority over published RAG/VQA methods without same-split reproduction",
            "lesion localization quality until the model outputs query-image boxes or masks",
        ],
        "next_dataset_steps": [
            "Add BTXRD loader for tumor presence and benign/malignant QA.",
            "Add GRAZPEDWRI-DX loader for pediatric wrist fracture hard-negative grounding.",
            "Add RadBench/ImageCLEF musculoskeletal subset as external native-VQA sanity check.",
        ],
    }


def scope_warnings(manifest: dict[str, Any]) -> list[str]:
    """Human-readable warnings for paper and UI surfaces."""
    active = manifest.get("active_dataset") if isinstance(manifest, dict) else None
    native_vqa = bool(active.get("native_vqa")) if isinstance(active, dict) else False
    warnings = []
    if not native_vqa:
        warnings.append(
            "The active dataset is not a native VQA dataset; questions are generated from image annotations."
        )
    warnings.append(
        "Grounding/localization claims require explicit query-image region output and IoU/Dice/mAP scoring."
    )
    warnings.append(
        "External native-VQA claims require RadBench/ImageCLEF/VQA-RAD-style reference answers."
    )
    return warnings
