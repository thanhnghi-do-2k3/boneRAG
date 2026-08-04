"""Unit tests for Milestone 3: Anatomical Reranker and Evidence Gate."""

from __future__ import annotations

import unittest

from bonerag.main_algo.data import ImageRecord
from bonerag.main_algo.gating import EvidenceGate, GateDecision
from bonerag.main_algo.reranker import AnatomicalReranker, RerankScore
from bonerag.main_algo.vector_index import SearchHit


class TestMilestone3RerankGate(unittest.TestCase):
    """Test suite for AnatomicalReranker and EvidenceGate."""

    def setUp(self) -> None:
        self.reranker = AnatomicalReranker()
        self.gate = EvidenceGate(min_similarity=0.02)
        self.test_record_fracture = ImageRecord(
            image_id="frac-wrist-001",
            title="Distal radius fracture",
            body_part="wrist",
            diagnosis="fracture",
            fracture_type="transverse",
            region="distal radius",
            evidence_note="Lucent line across distal radius",
            text="wrist distal radius transverse fracture xray",
        )
        self.test_record_normal = ImageRecord(
            image_id="normal-wrist-022",
            title="Normal wrist reference",
            body_part="wrist",
            diagnosis="normal",
            fracture_type="none",
            region="carpal and distal forearm",
            evidence_note="No cortical break",
            text="normal wrist xray no fracture",
        )

    def test_anatomy_token_extraction(self) -> None:
        tokens = self.reranker.extract_anatomy_tokens("Wrist fracture distal radius X-ray")
        self.assertIn("wrist", tokens)

    def test_pathology_score_matching(self) -> None:
        score_frac = self.reranker.compute_rerank_score(
            question="Wrist fracture X-ray",
            record=self.test_record_fracture,
            vector_similarity=0.85,
        )
        self.assertEqual(score_frac.pathology_score, 1.0)
        self.assertGreater(score_frac.final_score, 0.5)

    def test_hard_negative_penalty(self) -> None:
        score_norm = self.reranker.compute_rerank_score(
            question="Severe wrist fracture distal radius",
            record=self.test_record_normal,
            vector_similarity=0.70,
        )
        self.assertGreater(score_norm.hard_negative_penalty, 0.0)

    def test_evidence_gating_accepted(self) -> None:
        hits = [SearchHit(record_id="frac-wrist-001", score=0.85)]
        decision = self.gate.evaluate_hits("Wrist fracture X-ray", hits)
        self.assertTrue(decision.passed)
        self.assertEqual(decision.decision_code, "ACCEPTED")

    def test_evidence_gating_low_similarity(self) -> None:
        hits = [SearchHit(record_id="frac-wrist-001", score=0.001)]
        decision = self.gate.evaluate_hits("Wrist fracture low similarity query", hits)
        self.assertFalse(decision.passed)
        self.assertEqual(decision.decision_code, "LOW_SIMILARITY")


if __name__ == "__main__":
    unittest.main()
