"""Unit tests for the reproducible FracAtlas benchmark protocol."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bonerag.evaluation.benchmark import (
    SYSTEMS,
    _diagnosis_from_text,
    aggregate_case_scores,
    benchmark_systems,
    build_cases,
    protocol_metadata,
)
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
        self.assertEqual(protocol["benchmark_version"], "bonerag-grounded-vqa-v5")
        self.assertEqual(protocol["task"], "FracAtlas-derived closed fracture grounded VQA pilot")
        self.assertEqual(protocol["vqa_task_scope"], "label-derived closed-ended VQA from FracAtlas annotations")
        self.assertFalse(protocol["native_vqa_dataset"])
        self.assertTrue(protocol["test_holdout"])
        self.assertTrue(protocol["test_ids_excluded_from_retrieval"])
        self.assertFalse(protocol["external_text_corpus"])
        self.assertFalse(protocol["official_paper_reproductions"])
        self.assertFalse(protocol["vqa_explanation_ground_truth"])
        self.assertFalse(protocol["query_localization_output_scored"])
        self.assertIn("grounded_vqa_manifest", protocol)
        self.assertIn("BTXRD/BTRXD", [item["label"] for item in protocol["grounded_vqa_manifest"]["datasets"]])
        self.assertEqual(len(SYSTEMS), 7)
        self.assertEqual(
            [system["key"] for system in SYSTEMS],
            [
                "image_rag",
                "zero_shot_prompt",
                "knn_majority",
                "knn_weighted",
                "centroid_classifier",
                "linear_probe",
                "bonerag",
            ],
        )
        self.assertEqual(len(benchmark_systems(include_controls=True)), 8)
        self.assertEqual(len(benchmark_systems(include_literature_proxies=True)), 7)
        self.assertEqual(len(benchmark_systems(include_controls=True, include_literature_proxies=True)), 8)

    def test_aggregate_reports_binary_diagnostic_metrics(self) -> None:
        scores = [
            {
                "expected_diagnosis": "fracture",
                "predicted_top_diagnosis": "fracture",
                "answer_predicted_diagnosis": "fracture",
                "decision_predicted_diagnosis": "fracture",
                "decision_label_accuracy": 1,
                "decision_confidence": 1,
                "retrieval_top1_label_accuracy": 1,
                "evidence_label_precision_at_4": 1,
                "evidence_label_recall_at_4": 1,
                "evidence_label_mrr": 1,
                "evidence_label_ndcg_at_4": 1,
                "evidence_label_consensus": 1,
                "answer_label_accuracy": 1,
                "answer_matches_top_evidence": 1,
                "answer_matches_evidence_majority": 1,
                "answer_factuality_score": 1,
                "latency_ms": 10,
            },
            {
                "expected_diagnosis": "normal",
                "predicted_top_diagnosis": "fracture",
                "answer_predicted_diagnosis": None,
                "decision_predicted_diagnosis": "fracture",
                "decision_label_accuracy": 0,
                "decision_confidence": 0.5,
                "retrieval_top1_label_accuracy": 0,
                "evidence_label_precision_at_4": 0.5,
                "evidence_label_recall_at_4": 1,
                "evidence_label_mrr": 0.5,
                "evidence_label_ndcg_at_4": 0.5,
                "evidence_label_consensus": 0.5,
                "answer_label_accuracy": 0,
                "answer_matches_top_evidence": 0,
                "answer_matches_evidence_majority": 0,
                "answer_factuality_score": 0.5,
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
        self.assertEqual(summary["answer_factuality_score"], 0.75)
        self.assertEqual(summary["decision_f1"], 0.6667)
        self.assertEqual(summary["decision_balanced_accuracy"], 0.5)

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
                        "body_part": "forearm/wrist",
                        "region": "forearm and wrist",
                        "text": "fracatlas normal xray wrist forearm bone case img0000477",
                    }
                ]),
                encoding="utf-8",
            )

            pipeline = BoneRAGPipeline(encoder=FakeEncoder(), metadata_path=metadata_path)

        self.assertEqual(pipeline.records[0].diagnosis, "normal")
        self.assertEqual(pipeline.records[0].fracture_type, "none")
        self.assertEqual(pipeline.records[0].image_id, "fracatlas-normal-img0000477")
        self.assertEqual(pipeline.records[0].body_part, "unlabeled anatomy")
        self.assertEqual(pipeline.records[0].region, "unlabeled anatomy")

    def test_metadata_loader_preserves_btxrd_tumor_records(self) -> None:
        class FakeEncoder:
            dim = 2

            def encode_text(self, text: str):
                return (1.0, 0.0)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            tumor_dir = root / "Benign Tumor"
            tumor_dir.mkdir()
            image_path = tumor_dir / "IMG000001.jpg"
            image_path.write_bytes(b"fake")
            metadata_path = root / "btxrd_biomedclip_metadata.json"
            metadata_path.write_text(
                json.dumps([
                    {
                        "dataset": "BTXRD",
                        "image_id": "btxrd-bone-tumor-benign-img000001",
                        "image_path": str(image_path),
                        "diagnosis": "bone_tumor",
                        "fracture_type": "none",
                        "tumor_type": "benign",
                        "title": "BTXRD bone tumor X-ray IMG000001.jpg",
                        "body_part": "tibia",
                        "region": "lower limb",
                        "text": "btxrd bone xray radiograph bone_tumor benign tibia",
                        "tumor_boxes": [[1.0, 2.0, 30.0, 40.0]],
                    }
                ]),
                encoding="utf-8",
            )

            pipeline = BoneRAGPipeline(encoder=FakeEncoder(), metadata_path=metadata_path)

        record = pipeline.records[0]
        self.assertEqual(record.image_id, "btxrd-bone-tumor-benign-img000001")
        self.assertEqual(record.diagnosis, "bone_tumor")
        self.assertEqual(record.fracture_type, "benign")
        self.assertEqual(record.fracture_boxes, [[1.0, 2.0, 30.0, 40.0]])
        self.assertTrue(record.image_path.endswith("IMG000001.jpg"))

    def test_answer_parser_prefers_bonerag_calibrated_footer(self) -> None:
        answer = (
            "Phần thân câu có thể nhắc no fracture và fracture lẫn nhau.\n\n"
            "Kết luận chuẩn hóa BoneRAG: fracture (gãy xương)."
        )
        self.assertEqual(_diagnosis_from_text(answer), "fracture")


if __name__ == "__main__":
    unittest.main()
