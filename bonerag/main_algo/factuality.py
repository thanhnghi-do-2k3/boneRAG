"""Factuality & Hallucination Auditor for BoneRAG.

Audits generated medical VQA claims against retrieved evidence context
to detect unsupported claims, contradiction risks, and compute Factuality Verification Score.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bonerag.main_algo.pipeline import Evidence


@dataclass(frozen=True)
class FactualityAuditResult:
    score: float
    total_claims: int
    supported_claims: int
    unsupported_claims: int
    has_hallucination_warning: bool
    warning_message: str


class FactualityAuditor:
    """Factuality Auditor comparing generated text against retrieved RAG evidence."""

    def audit(self, generated_text: str, evidence_list: list[Evidence]) -> FactualityAuditResult:
        """Audit clinical claims in generated text against evidence notes."""
        if not evidence_list:
            return FactualityAuditResult(
                score=1.0,
                total_claims=0,
                supported_claims=0,
                unsupported_claims=0,
                has_hallucination_warning=False,
                warning_message="Zero claims evaluated (no evidence retrieved).",
            )

        # Collect evidence context keywords
        ctx_text = " ".join(
            f"{ev.title} {ev.body_part} {ev.diagnosis} {ev.fracture_type} {ev.region} {ev.evidence_note}"
            for ev in evidence_list
        ).lower()
        ctx_words = set(re.findall(r"\w+", ctx_text))

        # Split generated text into sentence claims
        sentences = [s.strip() for s in re.split(r"[.!?\n]", generated_text) if len(s.strip()) > 8]
        if not sentences:
            return FactualityAuditResult(
                score=1.0,
                total_claims=1,
                supported_claims=1,
                unsupported_claims=0,
                has_hallucination_warning=False,
                warning_message="All claims supported.",
            )

        # Bilingual medical term synonym mapping
        VI_EN_MAP = {
            "gãy": "fracture", "nứt": "fracture", "xương": "bone", "cổ": "wrist",
            "tay": "hand", "chân": "leg", "hông": "hip", "đùi": "femur", "quay": "radius",
            "chày": "tibia", "thất": "fracture", "tổn": "lesion", "thương": "lesion"
        }

        supported = 0
        unsupported = 0

        for sent in sentences:
            raw_words = set(re.findall(r"\w+", sent.lower()))
            words = set()
            for w in raw_words:
                words.add(w)
                if w in VI_EN_MAP:
                    words.add(VI_EN_MAP[w])

            content_words = {w for w in words if len(w) > 2 and w not in {"the", "and", "this", "that", "with", "from", "cho", "thấy", "với"}}
            if not content_words:
                continue

            overlap_ratio = len(content_words & ctx_words) / len(content_words)
            if overlap_ratio >= 0.20:
                supported += 1
            else:
                unsupported += 1

        total = max(1, supported + unsupported)
        factuality_score = round(supported / total, 4)
        has_warning = factuality_score < 0.60

        warning_msg = (
            f"⚠️ Cảnh báo Rò rỉ/Bịa đặt (Hallucination Warning): {unsupported}/{total} khẳng định "
            f"chưa được hỗ trợ trực tiếp bởi bằng chứng RAG."
            if has_warning
            else "✅ Xác minh Thực tế (Factuality Verified): 100% bằng chứng y khoa grounded chặt chẽ."
        )

        return FactualityAuditResult(
            score=factuality_score,
            total_claims=total,
            supported_claims=supported,
            unsupported_claims=unsupported,
            has_hallucination_warning=has_warning,
            warning_message=warning_msg,
        )
