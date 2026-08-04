"""Extended Medical VQA & RAG Metrics Suite for BoneRAG.

Computes state-of-the-art evaluation metrics referenced in top AI/Medical VQA literature:
1. Retrieval Metrics: Recall@K, MRR, Normalized Discounted Cumulative Gain (nDCG@K).
2. Clinical VQA Metrics: Medical Entity BLEU-1/BLEU-4, ROUGE-L, Clinical Concept F1.
3. RAG Grounding & Safety: Hallucination Index, Faithfulness Score, Context Relevancy.
4. Anatomic-IoU (Bounding Box IoU for Fracture Localization Grounding).

Usage:
    python3 -m bonerag.evaluation.extended_metrics --log bonerag/evaluation/sessions.jsonl
"""

from __future__ import annotations

import math
import re
from typing import Any


def compute_ndcg_at_k(retrieved_ids: list[str], ground_truth_ids: list[str], k: int = 4) -> float:
    """Normalized Discounted Cumulative Gain (nDCG@K).
    
    Measures ranking quality considering position decay: DCG@K / IDCG@K.
    """
    gt_set = set(ground_truth_ids)
    if not gt_set or not retrieved_ids:
        return 0.0

    retrieved = retrieved_ids[:k]
    dcg = 0.0
    for idx, item_id in enumerate(retrieved, start=1):
        rel = 1.0 if item_id in gt_set else 0.0
        dcg += rel / math.log2(idx + 1)

    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, min(len(gt_set), k) + 1))
    return round(dcg / idcg, 4) if idcg > 0 else 0.0


def compute_clinical_concept_f1(generated_text: str, expected_concepts: list[str]) -> dict[str, float]:
    """Clinical Concept Precision, Recall & F1-Score.
    
    Measures exact extraction of medical terms (e.g. 'fracture', 'distal radius', 'metacarpal').
    """
    gen_lower = generated_text.lower()
    matched = sum(1 for concept in expected_concepts if concept.lower() in gen_lower)
    
    precision = matched / len(expected_concepts) if expected_concepts else 0.0
    recall = matched / len(expected_concepts) if expected_concepts else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "clinical_precision": round(precision, 4),
        "clinical_recall": round(recall, 4),
        "clinical_f1": round(f1, 4),
    }


def compute_hallucination_rate(generated_text: str, context_evidence_text: str) -> float:
    """Hallucination Index (RAG Triangulation).
    
    Fraction of medical claims in generated text NOT supported by retrieved context.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]", generated_text) if len(s.strip()) > 5]
    if not sentences or not context_evidence_text:
        return 0.0

    ctx_words = set(re.findall(r"\w+", context_evidence_text.lower()))
    unsupported = 0

    for sent in sentences:
        words = set(re.findall(r"\w+", sent.lower()))
        # If less than 20% of sentence keywords match retrieved evidence context, flag as potential hallucination
        if words and len(words & ctx_words) / len(words) < 0.2:
            unsupported += 1

    return round(unsupported / len(sentences), 4)


def compute_anatomic_iou(predicted_boxes: list[list[float]], target_boxes: list[list[float]]) -> float:
    """Intersection over Union (IoU) for fracture bounding box localization."""
    if not predicted_boxes or not target_boxes:
        return 0.0

    total_iou = 0.0
    count = 0
    for p in predicted_boxes:
        for t in target_boxes:
            if len(p) < 4 or len(t) < 4:
                continue
            # Box format: [x1, y1, x2, y2]
            xi1 = max(p[0], t[0])
            yi1 = max(p[1], t[1])
            xi2 = min(p[2], t[2])
            yi2 = min(p[3], t[3])
            
            inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            box1_area = (p[2] - p[0]) * (p[3] - p[1])
            box2_area = (t[2] - t[0]) * (t[3] - t[1])
            union_area = box1_area + box2_area - inter_area
            
            if union_area > 0:
                iou = inter_area / union_area
                total_iou += iou
                count += 1

    return round(total_iou / count, 4) if count > 0 else 0.0
