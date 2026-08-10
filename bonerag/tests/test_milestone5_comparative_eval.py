"""Unit tests for the reproducible FracAtlas benchmark protocol."""

from __future__ import annotations

import unittest

from bonerag.evaluation.benchmark import SYSTEMS, build_cases, protocol_metadata
from bonerag.main_algo.data import SAMPLE_RECORDS


class TestMilestone5ComparativeEval(unittest.TestCase):
    """Test the deterministic case and system contract without model downloads."""

    def test_builds_balanced_real_cases(self) -> None:
        cases = build_cases(SAMPLE_RECORDS, cases_per_label=2)
        self.assertEqual([case.expected_diagnosis for case in cases], [
            "fracture", "fracture", "normal", "normal",
        ])
        self.assertTrue(all(case.query_image_path for case in cases))

    def test_protocol_declares_holdout_and_systems(self) -> None:
        protocol = protocol_metadata(build_cases(SAMPLE_RECORDS, cases_per_label=2))
        self.assertEqual(protocol["benchmark_version"], "bonerag-fracatlas-image-v1")
        self.assertTrue(protocol["test_holdout"])
        self.assertTrue(protocol["test_ids_excluded_from_retrieval"])
        self.assertEqual(len(SYSTEMS), 4)


if __name__ == "__main__":
    unittest.main()
