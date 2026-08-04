"""Unit tests for Milestone 4: Evidence Citation Synthesizer and Factuality Auditor."""

from __future__ import annotations

import unittest

from bonerag.main_algo.citation_synthesizer import EvidenceCitationSynthesizer
from bonerag.main_algo.factuality import FactualityAuditor, FactualityAuditResult
from bonerag.main_algo.pipeline import Evidence


class TestMilestone4GeneratorFactuality(unittest.TestCase):
    """Test suite for EvidenceCitationSynthesizer and FactualityAuditor."""

    def setUp(self) -> None:
        self.synthesizer = EvidenceCitationSynthesizer()
        self.auditor = FactualityAuditor()
        self.test_evidence = [
            Evidence(
                image_id="frac-wrist-001",
                image_path="/tmp/wrist.jpg",
                image_width=512,
                image_height=512,
                fracture_boxes=[[10.0, 10.0, 100.0, 100.0]],
                title="Distal radius fracture",
                body_part="wrist",
                diagnosis="fracture",
                fracture_type="transverse",
                region="distal radius",
                evidence_note="Lucent fracture line across distal radius",
                retrieval_score=0.88,
                rerank_score=0.92,
            )
        ]

    def test_citation_formatting(self) -> None:
        formatted = self.synthesizer.format_citations(self.test_evidence)
        self.assertIn("frac-wrist-001", formatted)
        self.assertIn("Trích dẫn Nguồn Bằng chứng X-quang", formatted)
        self.assertIn("Tọa độ BBox ROI", formatted)

    def test_inline_citation_attachment(self) -> None:
        attached = self.synthesizer.attach_inline_citations("Ghi nhận gãy cổ tay.", self.test_evidence)
        self.assertIn("[Doc: `frac-wrist-001`]", attached)

    def test_factuality_audit_high_score(self) -> None:
        generated_ans = "X-quang cho thấy gãy cổ tay vị trí distal radius với vết nứt rõ rệt."
        result = self.auditor.audit(generated_ans, self.test_evidence)
        self.assertGreaterEqual(result.score, 0.60)
        self.assertFalse(result.has_hallucination_warning)

    def test_factuality_audit_hallucination_warning(self) -> None:
        generated_ans = "Bệnh nhân bị u não sọ não thất và tổn thương tim nghiêm trọng không liên quan."
        result = self.auditor.audit(generated_ans, self.test_evidence)
        self.assertLess(result.score, 0.60)
        self.assertTrue(result.has_hallucination_warning)


if __name__ == "__main__":
    unittest.main()
