"""Tests for paper-ready benchmark post-processing."""

from __future__ import annotations

import unittest

from bonerag.evaluation.paper_report import (
    build_artifact_bundle,
    build_markdown_report,
    build_paper_evaluation,
)


def _row(system_key: str, case_id: str, expected: str, top: str, answer: str, latency: float) -> dict:
    correct_top = float(top == expected)
    correct_answer = float(answer == expected)
    return {
        "case_id": case_id,
        "query_image_id": f"img-{case_id}",
        "system_key": system_key,
        "system_label": "BoneRAG (ours)" if system_key == "bonerag" else "Image-only RAG",
        "expected_diagnosis": expected,
        "predicted_top_diagnosis": top,
        "evidence_majority_diagnosis": top,
        "answer_predicted_diagnosis": answer,
        "retrieval_top1_label_accuracy": correct_top,
        "evidence_label_precision_at_4": correct_top,
        "evidence_label_recall_at_4": correct_top,
        "evidence_label_mrr": correct_top,
        "evidence_label_ndcg_at_4": correct_top,
        "answer_label_accuracy": correct_answer,
        "answer_matches_top_evidence": float(answer == top),
        "answer_matches_evidence_majority": float(answer == top),
        "answer_factuality_score": 1.0 if answer == top else 0.5,
        "answer_hallucination_warning": False,
        "answer_supported_claims": 1,
        "answer_unsupported_claims": 0,
        "latency_ms": latency,
        "top_evidence_id": f"ev-{case_id}",
    }


class TestPaperReport(unittest.TestCase):
    def _sample_run(self) -> dict:
        cases = [
            _row("image_rag", "fracture-001", "fracture", "normal", "normal", 20),
            _row("bonerag", "fracture-001", "fracture", "fracture", "fracture", 24),
            _row("image_rag", "fracture-002", "fracture", "fracture", "fracture", 21),
            _row("bonerag", "fracture-002", "fracture", "fracture", "fracture", 23),
            _row("image_rag", "normal-001", "normal", "normal", "normal", 19),
            _row("bonerag", "normal-001", "normal", "normal", "normal", 21),
            _row("image_rag", "normal-002", "normal", "fracture", "fracture", 22),
            _row("bonerag", "normal-002", "normal", "normal", "normal", 22),
        ]
        return {
            "run_id": "benchmark-test",
            "created_at": "2026-08-13T00:00:00Z",
            "protocol": {
                "benchmark_version": "bonerag-fracatlas-image-v3",
                "dataset": "FracAtlas",
                "dataset_fingerprint": "unit-test",
                "n_cases": 4,
                "test_holdout": True,
                "test_ids_excluded_from_retrieval": True,
                "official_paper_reproductions": False,
                "vqa_explanation_ground_truth": False,
            },
            "encoder": "biomedclip",
            "generator": "local_context_synth",
            "systems": [
                {"system_key": "image_rag", "system_label": "Image-only RAG", "n_cases": 4},
                {"system_key": "bonerag", "system_label": "BoneRAG (ours)", "n_cases": 4},
            ],
            "cases": cases,
        }

    def test_builds_ci_and_paired_claim_guidance(self) -> None:
        paper = build_paper_evaluation(self._sample_run())
        self.assertEqual(paper["schema_version"], "paper-eval-v1")
        self.assertEqual(len(paper["systems"]), 2)
        top1_metric = paper["systems"][1]["metrics"]["retrieval_top1_label_accuracy"]
        self.assertEqual(top1_metric["successes"], 4)
        self.assertIsNotNone(top1_metric["ci95"])

        top1_pair = next(
            item for item in paper["paired_comparisons"]
            if item["metric"] == "retrieval_top1_label_accuracy"
        )
        self.assertEqual(top1_pair["mcnemar_b_method_correct_only"], 2)
        self.assertEqual(top1_pair["mcnemar_c_baseline_correct_only"], 0)
        self.assertIn("MMed-RAG", " ".join(paper["claim_guidance"]["blocked"]))

    def test_artifact_bundle_contains_paper_outputs(self) -> None:
        run = self._sample_run()
        run["paper_evaluation"] = build_paper_evaluation(run)
        markdown = build_markdown_report(run)
        bundle = build_artifact_bundle(run)
        self.assertIn("BoneRAG Benchmark Paper Evaluation", markdown)
        self.assertIn("markdown_report", bundle)
        self.assertIn("systems_csv", bundle)
        self.assertIn("summary_svg", bundle)


if __name__ == "__main__":
    unittest.main()
