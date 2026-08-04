"""Automated Comparative Benchmark Matrix & Experiment Logger for BoneRAG.

Runs 4-layer comparative evaluation matrix across SOTA baselines:
1. Baseline 1: No-RAG (Direct Zero-Shot Generation)
2. Baseline 2: Text-Only RAG (Traditional Document RAG)
3. Baseline 3: Standard Multimodal CLIP RAG (No Rerank & No Gate)
4. Proposed: Full BoneRAG Pipeline (Milestone 1-4 Complete)

Usage:
    python3 -m bonerag.evaluation.run_benchmark
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from bonerag.evaluation.evaluator import BoneRAGEvaluator
from bonerag.main_algo.encoder import get_multimodal_encoder
from bonerag.main_algo.generator import LocalRAGSynthesizer
from bonerag.main_algo.pipeline import BoneRAGPipeline


def run_benchmark_matrix() -> list[dict]:
    evaluator = BoneRAGEvaluator()
    ground_truth = evaluator.ground_truth
    experiments_log_path = Path(__file__).resolve().parent / "experiments.jsonl"

    baselines_to_test = [
        ("1. No-RAG (Direct Zero-Shot)", "no_rag", "biomedclip"),
        ("2. Text-Only RAG", "text_only", "hashing"),
        ("3. Standard CLIP RAG (No Rerank/Gate)", "standard_clip", "clip_vit_b32"),
        ("4. Proposed BoneRAG Pipeline", "full_bonerag", "biomedclip"),
    ]

    results = []

    for label, mode_key, enc_key in baselines_to_test:
        print(f"\n⚡ [Benchmark Matrix] Testing Configuration: {label}...")
        try:
            encoder = get_multimodal_encoder(mode=enc_key)
            generator = LocalRAGSynthesizer()
            pipeline = BoneRAGPipeline(encoder=encoder, generator=generator)

            # Adjust pipeline settings according to baseline mode
            if mode_key == "standard_clip":
                pipeline.reranker.weight_anatomy = 0.0
                pipeline.reranker.weight_pathology = 0.0
                pipeline.reranker.hard_negative_penalty = 0.0

            sessions = []
            start_total = time.perf_counter()

            for item in ground_truth:
                question = item["question"]
                t0 = time.perf_counter()

                if mode_key == "no_rag":
                    answer = generator.generate(question, [], used_retrieval=False)
                    t1 = time.perf_counter()
                    latency_ms = int((t1 - t0) * 1000)
                    sessions.append({
                        "question_raw": question,
                        "answer": answer,
                        "evidence": [],
                        "retrieval": {"hits": []},
                        "latency_ms": latency_ms,
                    })
                else:
                    res = pipeline.answer(question)
                    t1 = time.perf_counter()
                    latency_ms = int((t1 - t0) * 1000)

                    raw_hits = res.debug.get("raw_hits", [])
                    hits_list = []
                    for h in raw_hits:
                        raw_id = h.get("record_id", "") if isinstance(h, dict) else getattr(h, "record_id", "")
                        parent_id = raw_id.split("#")[0] if raw_id else ""
                        score = h.get("score", 0.0) if isinstance(h, dict) else getattr(h, "score", 0.0)
                        hits_list.append({"record_id": parent_id, "score": score})

                    sessions.append({
                        "question_raw": question,
                        "answer": res.answer,
                        "evidence": [{"image_id": ev.image_id, "rerank_score": ev.rerank_score} for ev in res.evidence],
                        "retrieval": {"hits": hits_list},
                        "latency_ms": latency_ms,
                    })

            elapsed_total = round(time.perf_counter() - start_total, 2)
            agg = evaluator.aggregate(sessions)
            agg["baseline_name"] = label
            agg["mode_key"] = mode_key
            agg["encoder_key"] = enc_key
            agg["total_time_sec"] = elapsed_total
            results.append(agg)

            # Log to experiments.jsonl
            with experiments_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(agg, ensure_ascii=False) + "\n")

            print(
                f"   => Recall@4: {agg.get('recall_at_4')} | MRR: {agg.get('mrr')} | "
                f"Accuracy: {agg.get('answer_label_accuracy')} | Faithfulness: {agg.get('faithfulness_score')} | Latency: {agg.get('latency_ms')} ms"
            )

        except Exception as exc:
            print(f"   ⚠️ Error running {label}: {exc}")

    return results


def print_markdown_report(results: list[dict]) -> None:
    print("\n" + "=" * 85)
    print("📊 BONERAG SOTA COMPARATIVE BENCHMARK MATRIX REPORT (30 TEST CASES)")
    print("=" * 85 + "\n")
    print("| Cấu hình Thử nghiệm | Recall@4 | MRR | Diagnosis Accuracy | Faithfulness Score | Latency (ms) |")
    print("|---|---|---|---|---|---|")
    for r in results:
        label = r.get("baseline_name", "Unknown")
        rec = r.get("recall_at_4", 0.0)
        mrr = r.get("mrr", 0.0)
        acc = r.get("answer_label_accuracy", 0.0)
        faith = r.get("faithfulness_score", 0.0)
        lat = r.get("latency_ms", 0.0)
        print(f"| {label} | {rec:.4f} | {mrr:.4f} | {acc:.4f} ({acc*100:.1f}%) | {faith:.4f} ({faith*100:.1f}%) | {lat:.1f} ms |")
    print("\n" + "=" * 85 + "\n")


def main() -> None:
    results = run_benchmark_matrix()
    print_markdown_report(results)


if __name__ == "__main__":
    main()
