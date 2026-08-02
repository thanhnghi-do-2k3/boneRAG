import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main_algo.pipeline import BoneRAGPipeline


class MainAlgoPipelineTest(unittest.TestCase):
    def test_retrieves_fracture_evidence(self):
        pipeline = BoneRAGPipeline()
        result = pipeline.answer("Does this wrist X-ray show a distal radius fracture?")
        self.assertTrue(result.used_retrieval)
        self.assertGreater(len(result.evidence), 0)
        self.assertIn("fracture", result.answer.lower())

    def test_skips_unrelated_question(self):
        pipeline = BoneRAGPipeline()
        result = pipeline.answer("What is retrieval augmented generation?")
        self.assertFalse(result.used_retrieval)
        self.assertEqual(result.evidence, [])

    def test_serializes_to_api_payload(self):
        pipeline = BoneRAGPipeline()
        payload = pipeline.answer("hip femoral neck fracture").to_dict()
        self.assertIn("answer", payload)
        self.assertIn("evidence", payload)
        self.assertIn("debug", payload)


if __name__ == "__main__":
    unittest.main()
