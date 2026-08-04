"""Automated Comparative Benchmark Matrix & Experiment Logger for BoneRAG.

Runs evaluation matrix across 4 Generator models:
1. LocalRAGSynthesizer (Pure Evidence Synthesizer - Fast Benchmark)
2. Qwen2.5-0.5B-Instruct (HuggingFace Neural SLM)
3. Qwen2.5-1.5B-Instruct (HuggingFace Neural SLM)
4. SmolLM2-1.7B-Instruct (HuggingFace Neural SLM)

Usage:
    python3 -m bonerag.evaluation.run_benchmark [--generator <synth|qwen05|qwen15|smol|all>] [--cases <count>]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from bonerag.evaluation.evaluator import BoneRAGEvaluator
from bonerag.main_algo.encoder import get_multimodal_encoder
from bonerag.main_algo.generator import LocalHuggingFaceGenerator, LocalRAGSynthesizer
from bonerag.main_algo.pipeline import BoneRAGPipeline


def run_benchmark_matrix(generator_mode: str = "synth", max_cases: int | None = None) -> list[dict]:
    evaluator = BoneRAGEvaluator()
    ground_truth = evaluator.ground_truth
    if max_cases and max_cases > 0:
        ground_truth = ground_truth[:max_cases]

    experiments_log_path = Path(__file__).resolve().parent / "experiments.jsonl"

    baselines_to_test = [
        ("1. No-RAG (Direct Zero-Shot)", "no_rag", "biomedclip"),
        ("2. Text-Only RAG", "text_only", "hashing"),
        ("3. Standard CLIP RAG (No Rerank/Gate)", "standard_clip", "clip_vit_b32"),
        ("4. Proposed BoneRAG Pipeline", "full_bonerag", "biomedclip"),
    ]

    generators_map = {
        "synth": [("Local Synthesizer", LocalRAGSynthesizer())],
        "qwen05": [("Qwen2.5-0.5B", LocalHuggingFaceGenerator("Qwen/Qwen2.5-0.5B-Instruct"))],
        "qwen15": [("Qwen2.5-1.5B", LocalHuggingFaceGenerator("Qwen/Qwen2.5-1.5B-Instruct"))],
        "smol": [("SmolLM2-1.7B", LocalHuggingFaceGenerator("HuggingFaceTB/SmolLM2-1.7B-Instruct"))],
    }

    if generator_mode == "all":
        gens_to_run = [
            ("Local Synthesizer", LocalRAGSynthesizer()),
            ("Qwen2.5-0.5B", LocalHuggingFaceGenerator("Qwen/Qwen2.5-0.5B-Instruct")),
            ("Qwen2.5-1.5B", LocalHuggingFaceGenerator("Qwen/Qwen2.5-1.5B-Instruct")),
            ("SmolLM2-1.7B", LocalHuggingFaceGenerator("HuggingFaceTB/SmolLM2-1.7B-Instruct")),
        ]
    else:
        gens_to_run = generators_map.get(generator_mode, generators_map["synth"])

    results = []

    for gen_label, generator in gens_to_run:
        print(f"\n🧠 [Generator Evaluator] Active Model: {gen_label}")
        for label, mode_key, enc_key in baselines_to_test:
            config_label = f"{label} ({gen_label})"
            print(f"   ⚡ Testing: {config_label} on {len(ground_truth)} cases...")
            try:
                encoder = get_multimodal_encoder(mode=enc_key)
                pipeline = BoneRAGPipeline(encoder=encoder, generator=generator)

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
                agg["baseline_name"] = config_label
                agg["mode_key"] = mode_key
                agg["encoder_key"] = enc_key
                agg["generator_type"] = gen_label
                agg["total_time_sec"] = elapsed_total
                results.append(agg)

                with experiments_log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(agg, ensure_ascii=False) + "\n")

                print(
                    f"      => Acc: {agg.get('answer_label_accuracy')} | "
                    f"Faithfulness: {agg.get('faithfulness_score')} | Latency: {agg.get('latency_ms')} ms"
                )

            except Exception as exc:
                print(f"      ⚠️ Error running {config_label}: {exc}")

    return results


def print_markdown_report(results: list[dict]) -> None:
    print("\n" + "=" * 90)
    print("📊 BONERAG SOTA MULTI-GENERATOR BENCHMARK REPORT")
    print("=" * 90 + "\n")
    print("| Cấu hình Thử nghiệm | Generator Model | Diagnosis Accuracy | Faithfulness Score | Latency (ms) |")
    print("|---|---|---|---|---|")
    for r in results:
        label = r.get("baseline_name", "Unknown")
        gen_name = r.get("generator_type", "Unknown")
        acc = r.get("answer_label_accuracy", 0.0)
        faith = r.get("faithfulness_score", 0.0)
        lat = r.get("latency_ms", 0.0)
        print(f"| {label} | {gen_name} | {acc:.4f} ({acc*100:.1f}%) | {faith:.4f} ({faith*100:.1f}%) | {lat:.1f} ms |")
    print("\n" + "=" * 90 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="BoneRAG Multi-Model Benchmark Suite")
    parser.add_argument("--generator", choices=["synth", "qwen05", "qwen15", "smol", "all"], default="synth")
    parser.add_argument("--cases", type=int, default=None, help="Max test cases to run")
    args = parser.parse_args()

    results = run_benchmark_matrix(generator_mode=args.generator, max_cases=args.cases)
    print_markdown_report(results)


if __name__ == "__main__":
    main()
