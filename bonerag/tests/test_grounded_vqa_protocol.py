"""Tests for the bone-grounded VQA benchmark manifest."""

from __future__ import annotations

import unittest

from bonerag.evaluation.grounded_vqa_protocol import (
    build_grounded_vqa_manifest,
    scope_warnings,
)


class TestGroundedVQAProtocol(unittest.TestCase):
    def test_manifest_separates_native_vqa_from_annotation_derived_datasets(self) -> None:
        manifest = build_grounded_vqa_manifest()
        datasets = {item["key"]: item for item in manifest["datasets"]}

        self.assertEqual(manifest["schema_version"], "bone-grounded-vqa-v1")
        self.assertFalse(datasets["fracatlas"]["native_vqa"])
        self.assertEqual(datasets["fracatlas"]["status"], "implemented_current_run")
        self.assertFalse(datasets["btxrd"]["native_vqa"])
        self.assertEqual(datasets["btxrd"]["status"], "loader_pending")
        self.assertTrue(datasets["radbench"]["native_vqa"])
        self.assertEqual(datasets["radbench"]["status"], "external_eval_pending")
        baselines = {item["key"]: item for item in manifest["baselines"]}
        self.assertTrue(baselines["linear_probe"]["implemented"])

    def test_warnings_block_overclaiming(self) -> None:
        manifest = build_grounded_vqa_manifest()
        warnings = " ".join(scope_warnings(manifest))
        blocked = " ".join(manifest["blocked_claims"])

        self.assertIn("not a native VQA dataset", warnings)
        self.assertIn("localization", warnings)
        self.assertIn("clinical diagnosis system", blocked)
        self.assertIn("published RAG/VQA methods", blocked)


if __name__ == "__main__":
    unittest.main()
