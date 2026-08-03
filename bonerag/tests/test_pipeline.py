import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from main_algo.encoder import get_multimodal_encoder
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
        encoder = get_multimodal_encoder(mode="biomedclip")
        vec_text = encoder.encode_text("distal radius fracture")
        self.assertGreater(len(vec_text), 0)

    def test_image_query_encoding(self):
        encoder = get_multimodal_encoder(mode="biomedclip")
        sample_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        vec = encoder.encode_image_from_base64(sample_base64)
        self.assertGreater(len(vec), 0)

        pipeline = BoneRAGPipeline(encoder=encoder)
        hits = pipeline.retrieve("Wrist fracture", image_data_url=sample_base64)
        self.assertGreater(len(hits), 0)


if __name__ == "__main__":
    unittest.main()
