"""Anatomical & Pathology Cross-Attribute Reranker for BoneRAG.

Reranks retrieved evidence hits using anatomical region alignment,
pathology diagnosis matching, and hard negative penalty weighting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bonerag.main_algo.data import ImageRecord
    from bonerag.main_algo.pipeline import Evidence
    from bonerag.main_algo.vector_index import SearchHit


ANATOMY_KEYWORDS: dict[str, set[str]] = {
    "wrist": {"wrist", "radius", "ulna", "carpal", "distal radius", "scaphoid", "cổ tay", "xương quay", "xương trụ"},
    "hand": {"hand", "metacarpal", "phalanges", "thumb", "finger", "bàn tay", "ngón tay"},
    "hip": {"hip", "femur", "femoral neck", "pelvis", "acetabulum", "hông", "xương đùi", "khung chậu"},
    "forearm": {"forearm", "radius", "ulna", "shaft", "cẳng tay"},
    "leg": {"leg", "tibia", "fibula", "knee", "patella", "ankle", "foot", "chân", "cẳng chân", "đầu gối", "cổ chân", "bàn chân", "xương chày", "xương mác"},
}

PATHOLOGY_KEYWORDS: set[str] = {
    "fracture",
    "fractured",
    "broken",
    "crack",
    "lesion",
    "tumor",
    "dislocation",
    "gãy",
    "nứt",
    "tổn thương",
    "trật khớp",
}


def _pathology_target_from_question(question: str) -> str | None:
    """Infer an asserted pathology target from the question, if any.

    Yes/no screening prompts such as "Does this X-ray show a fracture?" should
    not bias the reranker toward fracture records; the image embedding should
    carry that decision. Asserted prompts such as "severe wrist fracture" still
    benefit from pathology-aware reranking.
    """
    q_lower = question.lower().strip()
    has_pathology_word = any(kw in q_lower for kw in PATHOLOGY_KEYWORDS)
    normal_patterns = (
        r"\bno\s+(?:acute\s+)?fracture\b",
        r"\bwithout\s+(?:a\s+)?fracture\b",
        r"\bnormal\b",
        r"không\s+(?:có\s+)?(?:gãy|fracture|xương gãy)",
        r"bình thường",
    )
    if any(re.search(pattern, q_lower) for pattern in normal_patterns):
        return "normal"

    screening_patterns = (
        r"^\s*(does|do|is|are|can|could|would|will|has|have)\b",
        r"\b(show|shows|detect|detects|indicate|indicates|evidence of)\b",
        r"\?$",
        r"\b(có|không|liệu|phải|chăng)\b.*\b(gãy|fracture)\b",
    )
    if has_pathology_word and any(re.search(pattern, q_lower) for pattern in screening_patterns):
        return None

    if has_pathology_word:
        return "fracture"
    return None


@dataclass
class RerankScore:
    parent_id: str
    final_score: float
    vector_score: float
    anatomy_score: float
    pathology_score: float
    hard_negative_penalty: float


class AnatomicalReranker:
    """Reranker combining Vision-Language vector similarity with anatomical & pathology priors."""

    def __init__(
        self,
        weight_sim: float = 0.50,
        weight_anatomy: float = 0.30,
        weight_pathology: float = 0.20,
        hard_negative_penalty: float = 0.35,
    ) -> None:
        self.weight_sim = weight_sim
        self.weight_anatomy = weight_anatomy
        self.weight_pathology = weight_pathology
        self.hard_negative_penalty = hard_negative_penalty

    def extract_anatomy_tokens(self, text: str) -> set[str]:
        text_lower = text.lower()
        found = set()
        for region, kw_set in ANATOMY_KEYWORDS.items():
            if any(kw in text_lower for kw in kw_set):
                found.add(region)
        return found

    def compute_rerank_score(
        self,
        question: str,
        record: ImageRecord,
        vector_similarity: float,
    ) -> RerankScore:
        q_lower = question.lower()
        rec_text = f"{record.body_part} {record.region} {record.title} {record.text}".lower()

        # 1. Anatomy Alignment Score
        q_anatomy = self.extract_anatomy_tokens(q_lower)
        rec_anatomy = self.extract_anatomy_tokens(rec_text)
        
        if q_anatomy and rec_anatomy:
            anatomy_match = len(q_anatomy & rec_anatomy) / len(q_anatomy)
        elif not q_anatomy:
            anatomy_match = 0.5  # Neutral if query doesn't specify anatomy
        else:
            anatomy_match = 0.0

        # 2. Pathology Finding Score
        pathology_target = _pathology_target_from_question(q_lower)
        rec_is_fractured = record.diagnosis.lower() == "fracture" or record.fracture_type.lower() != "none"

        if pathology_target is None:
            pathology_score = 0.5
        elif pathology_target == "fracture" and rec_is_fractured:
            pathology_score = 1.0
        elif pathology_target == "normal" and not rec_is_fractured:
            pathology_score = 1.0
        else:
            pathology_score = 0.2

        # 3. Hard Negative Mining Penalty
        # Penalty if anatomy matches but pathology is opposite (e.g., normal case when user asks for severe fracture)
        penalty = 0.0
        if pathology_target == "fracture" and not rec_is_fractured and anatomy_match > 0.5:
            penalty = self.hard_negative_penalty

        final_score = (
            self.weight_sim * vector_similarity
            + self.weight_anatomy * anatomy_match
            + self.weight_pathology * pathology_score
            - penalty
        )

        return RerankScore(
            parent_id=record.image_id,
            final_score=round(max(0.0, final_score), 4),
            vector_score=round(vector_similarity, 4),
            anatomy_score=round(anatomy_match, 4),
            pathology_score=round(pathology_score, 4),
            hard_negative_penalty=round(penalty, 4),
        )

    def rerank_records(
        self,
        question: str,
        hits: list[SearchHit],
        record_by_id: dict[str, ImageRecord],
        top_k: int = 4,
    ) -> list[Evidence]:
        from bonerag.main_algo.pipeline import Evidence

        scored_evidence: list[tuple[float, Evidence]] = []

        for hit in hits:
            parent_id = hit.record_id.split("#")[0]
            if parent_id not in record_by_id:
                continue
            rec = record_by_id[parent_id]
            rerank_meta = self.compute_rerank_score(question, rec, hit.score)

            ev = Evidence(
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
                evidence_note=(
                    f"{rec.evidence_note} [Rerank Details: AnatomyMatch={rerank_meta.anatomy_score:.2f}, "
                    f"PathologyScore={rerank_meta.pathology_score:.2f}, Penalty={rerank_meta.hard_negative_penalty:.2f}]"
                ),
                retrieval_score=hit.score,
                rerank_score=rerank_meta.final_score,
            )
            scored_evidence.append((rerank_meta.final_score, ev))

        # Sort descending by final rerank score
        scored_evidence.sort(key=lambda item: item[0], reverse=True)
        return [ev for _, ev in scored_evidence[:top_k]]
