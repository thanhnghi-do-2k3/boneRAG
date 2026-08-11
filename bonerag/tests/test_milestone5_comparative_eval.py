"""Unit tests for the reproducible FracAtlas benchmark protocol."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bonerag.evaluation.benchmark import SYSTEMS, aggregate_case_scores, build_cases, protocol_metadata
from bonerag.main_algo.data import SAMPLE_RECORDS
from bonerag.main_algo.pipeline import BoneRAGPipeline


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
        self.assertEqual(len(SYSTEMS), 7)

    def test_aggregate_reports_binary_diagnostic_metrics(self) -> None:
        scores = [
            {
                "expected_diagnosis": "fracture",
                "predicted_top_diagnosis": "fracture",
                "answer_predicted_diagnosis": "fracture",
                "retrieval_top1_label_accuracy": 1,
                "evidence_label_precision_at_4": 1,
                "evidence_label_recall_at_4": 1,
                "evidence_label_mrr": 1,
                "evidence_label_ndcg_at_4": 1,
                "answer_label_accuracy": 1,
                "latency_ms": 10,
            },
            {
                "expected_diagnosis": "normal",
                "predicted_top_diagnosis": "fracture",
                "answer_predicted_diagnosis": None,
                "retrieval_top1_label_accuracy": 0,
                "evidence_label_precision_at_4": 0.5,
                "evidence_label_recall_at_4": 1,
                "evidence_label_mrr": 0.5,
                "evidence_label_ndcg_at_4": 0.5,
                "answer_label_accuracy": 0,
                "latency_ms": 20,
            },
        ]
        summary = aggregate_case_scores(scores)
        self.assertEqual(summary["retrieval_tp"], 1)
        self.assertEqual(summary["retrieval_fp"], 1)
        self.assertEqual(summary["retrieval_specificity"], 0.0)
        self.assertEqual(summary["answer_unknown"], 1)
        self.assertEqual(summary["answer_sensitivity"], 1.0)
        self.assertEqual(summary["answer_specificity"], 0.0)

    def test_metadata_loader_canonicalizes_fracatlas_ids_from_path_label(self) -> None:
        class FakeEncoder:
            dim = 2

            def encode_text(self, text: str):
                return (1.0, 0.0)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            normal_dir = root / "Non_fractured"
            normal_dir.mkdir()
            image_path = normal_dir / "IMG0000477.jpg"
            image_path.write_bytes(b"fake")
            metadata_path = root / "metadata.json"
            metadata_path.write_text(
                json.dumps([
                    {
                        "image_id": "fracatlas-fractured-img0000477",
                        "image_path": str(image_path),
                        "diagnosis": "fracture",
                        "fracture_type": "fractured",
                        "title": "mislabeled metadata",
                    }
                ]),
                encoding="utf-8",
            )

            pipeline = BoneRAGPipeline(encoder=FakeEncoder(), metadata_path=metadata_path)

        self.assertEqual(pipeline.records[0].diagnosis, "normal")
        self.assertEqual(pipeline.records[0].fracture_type, "none")
        self.assertEqual(pipeline.records[0].image_id, "fracatlas-normal-img0000477")


if __name__ == "__main__":
    unittest.main()
