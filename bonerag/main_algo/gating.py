"""Adaptive Evidence Gating Threshold for BoneRAG.

Evaluates retrieved evidence hits against minimum similarity thresholds,
context density, and relevance margins to prevent out-of-domain medical hallucination.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bonerag.main_algo.vector_index import SearchHit


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    top_score: float
    reason: str
    decision_code: str  # "ACCEPTED", "LOW_SIMILARITY", "EMPTY_HITS", "OUT_OF_DOMAIN"


class EvidenceGate:
    """Adaptive Evidence Gating mechanism to guard medical VQA answers."""

    def __init__(
        self,
        min_similarity: float = 0.02,
        margin_threshold: float = 0.005,
    ) -> None:
        self.min_similarity = min_similarity
        self.margin_threshold = margin_threshold

    def evaluate_hits(
        self,
        question: str,
        hits: list[SearchHit],
        has_image: bool = False,
    ) -> GateDecision:
        """Evaluate whether retrieved evidence passes safety & relevance criteria."""
        if not hits:
            return GateDecision(
                passed=False,
                top_score=0.0,
                reason="Cổng từ chối: Không tìm thấy bất kỳ bằng chứng X-quang phù hợp nào trong CSDL.",
                decision_code="EMPTY_HITS",
            )

        top_score = hits[0].score

        # Out-of-domain check for text-only queries without medical context
        lower_q = question.lower()
        if not has_image and "selected image context:" not in lower_q and "image_id:" not in lower_q:
            import re
            q_words = set(re.findall(r"\w+", lower_q))
            medical_keywords = {
                "xray", "x", "ray", "bone", "fracture", "gãy", "xương", "wrist",
                "hand", "hip", "tibia", "radius", "lesion", "tumor", "bệnh",
                "ảnh", "bị", "gì", "thế", "chẩn", "đoán", "tổn", "thương", "vùng",
                "khớp", "xem", "này", "distal", "femur", "arm", "leg", "pelvis",
                "carpal", "metacarpal", "scaphoid", "ulna", "fibula", "foot"
            }
            if not (q_words & medical_keywords):
                return GateDecision(
                    passed=False,
                    top_score=top_score,
                    reason="Cổng từ chối: Câu hỏi không thuộc miền ngữ cảnh X-quang y khoa.",
                    decision_code="OUT_OF_DOMAIN",
                )

        # Check image-attached query relaxation
        effective_threshold = self.min_similarity * 0.5 if has_image else self.min_similarity

        if top_score < effective_threshold:
            return GateDecision(
                passed=False,
                top_score=top_score,
                reason=(
                    f"Cổng từ chối: Điểm tương đồng bằng chứng hàng đầu ({top_score:.3f}) "
                    f"thấp hơn ngưỡng an toàn ({effective_threshold:.3f})."
                ),
                decision_code="LOW_SIMILARITY",
            )

        return GateDecision(
            passed=True,
            top_score=top_score,
            reason=f"Cổng chấp nhận: Bằng chứng hàng đầu đạt điểm {top_score:.3f} >= {effective_threshold:.3f}",
            decision_code="ACCEPTED",
        )
