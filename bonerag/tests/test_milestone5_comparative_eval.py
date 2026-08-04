"""Unit tests for Milestone 5: Comparative Evaluation Matrix."""

from __future__ import annotations

import unittest

from bonerag.evaluation.evaluator import BoneRAGEvaluator
from bonerag.evaluation.run_benchmark import run_benchmark_matrix


class TestMilestone5ComparativeEval(unittest.TestCase):
    """Test suite for Milestone 5 comparative matrix."""

    def setUp(self) -> None:
        self.evaluator = BoneRAGEvaluator()

    def test_ground_truth_cases_loaded(self) -> None:
        gt = self.evaluator.ground_truth
        self.assertGreaterEqual(len(gt), 30)

    def test_run_benchmark_matrix_structure(self) -> None:
        results = run_benchmark_matrix()
        self.assertEqual(len(results), 4)
        for r in results:
            self.assertIn("baseline_name", r)
            self.assertIn("recall_at_4", r)
            self.assertIn("mrr", r)
            self.assertIn("answer_label_accuracy", r)
            self.assertIn("faithfulness_score", r)


if __name__ == "__main__":
    unittest.main()
