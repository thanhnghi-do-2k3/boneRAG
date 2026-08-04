"""Automated Benchmark Suite for BoneRAG.

Runs evaluation matrix across combinations of Encoders and Generators on Ground Truth test cases,
computing Recall@K, MRR, Diagnosis Accuracy, Faithfulness, Context Relevance, and Latency.

Usage:
    python3 -m bonerag.evaluation.run_benchmark
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from bonerag.evaluation.evaluator import BoneRAGEvaluator
from bonerag.main_algo.encoder import get_multimodal_encoder
from bonerag.main_algo.generator import (
    LocalRAGSynthesizer,
    LocalHuggingFaceGenerator,
)
from bonerag.main_algo.pipeline import BoneRAGPipeline
from bonerag.main_algo.vector_index import get_vector_index


def run_benchmark_matrix() -> list[dict]:
    evaluator = BoneRAGEvaluator()
    ground_truth = evaluator.ground_truth

    encoders_to_test = [
        ("biomedclip", "BiomedCLIP (Microsoft)"),
        ("hashing", "Hashing Baseline"),
    ]

    results = []

    for enc_key, enc_label in encoders_to_test:
        print(f"\n⚡ [Benchmark] Testing Encoder: {enc_label} ({enc_key})...")
        try:
            encoder = get_multimodal_encoder(mode=enc_key)
            generator = LocalRAGSynthesizer()
            pipeline = BoneRAGPipeline(encoder=encoder, generator=generator)

            sessions = []
            start_total = time.perf_counter()

            for item in ground_truth:
                question = item["question"]
                t0 = time.perf_counter()

                # Execute pipeline retrieval & generation
                res = pipeline.answer(question)
                t1 = time.perf_counter()
                latency_ms = int((t1 - t0) * 1000)

                session_log = {
                    "question_raw": question,
                    "answer": res.answer,
                    "evidence": [
                        {
                            "image_id": ev.image_id,
                            "rerank_score": ev.rerank_score,
                        }
                        for ev in res.evidence
                    ],
                    "retrieval": {
                        "hits": [
                            {"record_id": hit.record_id, "score": hit.score}
                            for hit in res.debug.get("raw_hits", [])
                        ]
                    },
                    "latency_ms": latency_ms,
                }
                sessions.append(session_log)

            elapsed_total = round(time.perf_counter() - start_total, 2)
            agg = evaluator.aggregate(sessions)
            agg["encoder"] = enc_label
            agg["encoder_key"] = enc_key
            agg["total_time_sec"] = elapsed_total
            results.append(agg)
            print(f"   => Recall@4: {agg.get('recall_at_4')} | MRR: {agg.get('mrr')} | Accuracy: {agg.get('answer_label_accuracy')} | Avg Latency: {agg.get('latency_ms')} ms")

        except Exception as exc:
            print(f"   ⚠️ Error running {enc_key}: {exc}")

    return results


def print_markdown_report(results: list[dict]) -> None:
    print("\n" + "=" * 80)
    print("📊 BONERAG BENCHMARK RESULTS REPORT")
    print("=" * 80 + "\n")
    print("| Encoder Backbone | Recall@4 | MRR | Diagnosis Accuracy | Faithfulness | Latency (ms) |")
    print("|---|---|---|---|---|---|")
    for r in results:
        enc = r.get("encoder", "Unknown")
        rec = r.get("recall_at_4", 0.0)
        mrr = r.get("mrr", 0.0)
        acc = r.get("answer_label_accuracy", 0.0)
        faith = r.get("faithfulness_score", 0.0)
        lat = r.get("latency_ms", 0)
        print(f"| {enc} | {rec:.4f} | {mrr:.4f} | {acc:.4f} | {faith:.4f} | {lat} ms |")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    benchmark_data = run_benchmark_matrix()
    print_markdown_report(benchmark_data)
