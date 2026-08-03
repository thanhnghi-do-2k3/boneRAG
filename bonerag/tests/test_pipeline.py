import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main_algo.encoder import HashingTextEncoder, get_multimodal_encoder
from main_algo.vector_index import FAISSVectorIndex, InMemoryVectorIndex, SearchHit, get_vector_index
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

    def test_multimodal_encoder_roi_and_image(self):
        encoder = get_multimodal_encoder(mode="hashing")
        vec_text = encoder.encode_text("distal radius fracture")
        vec_img = encoder.encode_image("test.jpg")
        vec_roi = encoder.encode_roi("test.jpg", [10.0, 20.0, 100.0, 100.0])
        self.assertEqual(len(vec_text), 256)
        self.assertEqual(len(vec_img), 256)
        self.assertEqual(len(vec_roi), 256)

    def test_vector_index_factory(self):
        index = get_vector_index(dim=256)
        index.add("rec-01", (0.1,) * 256)
        hits = index.search((0.1,) * 256, top_k=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].record_id, "rec-01")


if __name__ == "__main__":
    unittest.main()
