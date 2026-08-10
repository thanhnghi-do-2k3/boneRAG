"""CLI for the reproducible FracAtlas Image-RAG benchmark.

This module intentionally does not read ``ground_truth.json``.  The query
label comes from the real FracAtlas folder containing the selected image, and
the same case list is used by the web benchmark endpoint.

Examples::

    python3 -m bonerag.evaluation.run_benchmark --generator synth
    python3 -m bonerag.evaluation.run_benchmark --generator qwen05 --cases 32
    python3 -m bonerag.evaluation.run_benchmark --generator all --cases 8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from bonerag.evaluation.benchmark import (
    SYSTEMS,
    aggregate_case_scores,
    build_cases,
    protocol_metadata,
    run_system_case,
)
from bonerag.main_algo.encoder import get_multimodal_encoder
from bonerag.main_algo.generator import get_generator
from bonerag.main_algo.pipeline import BoneRAGPipeline


GENERATOR_MODES = {
    "synth": "local_context_synth",
    "qwen05": "qwen_05b",
    "qwen15": "qwen_15b",
    "smol": "smollm_17b",
}


def _index_paths(encoder_name: str) -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    index_name = (
        "biomedclip"
        if "biomed" in encoder_name
        else "clip_vitl14"
        if "l14" in encoder_name
        else "clip_vitb32"
    )
    index_path = repo_root / f"fracatlas_{index_name}.faiss"
    metadata_path = repo_root / f"fracatlas_{index_name}_metadata.json"
    missing = [str(path) for path in (index_path, metadata_path) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Thiếu artifact offline của FracAtlas: " + ", ".join(missing) + ". "
            "Hãy chạy notebook index trước; CLI không được phép dùng toy corpus."
        )
    return index_path, metadata_path


def _make_pipeline(encoder_name: str, generator_name: str) -> BoneRAGPipeline:
    index_path, metadata_path = _index_paths(encoder_name)
    try:
        encoder = get_multimodal_encoder(mode=encoder_name, strict=True)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Thiếu dependency của encoder thật. Trên Colab hãy chạy: "
            "pip install -q torch open_clip_torch faiss-cpu pillow tqdm huggingface_hub"
        ) from exc
    return BoneRAGPipeline(
        encoder=encoder,
        generator=get_generator(generator_name, strict=True),
        top_k=4,
        min_similarity=0.02,
        index_path=index_path,
        metadata_path=metadata_path,
    )


def _run_generator_matrix(
    generator_name: str,
    encoder_name: str,
    cases_per_label: int,
) -> dict[str, Any]:
    pipeline = _make_pipeline(encoder_name, generator_name)
    cases = build_cases(pipeline.records, cases_per_label=cases_per_label)
    protocol = protocol_metadata(cases)
    test_query_ids = {case.query_image_id for case in cases}
    system_results: list[dict[str, Any]] = []

    print(
        f"[benchmark] {protocol['benchmark_version']} | "
        f"{len(cases)} real images | encoder={encoder_name} | generator={generator_name}"
    )
    print(f"[benchmark] fingerprint={protocol['dataset_fingerprint']}")

    for system in SYSTEMS:
        case_scores: list[dict[str, Any]] = []
        print(f"[benchmark] system={system['label']}")
        for index, case in enumerate(cases, start=1):
            result = run_system_case(pipeline, case, system, test_query_ids=test_query_ids)
            case_scores.append(result)
            print(
                f"  [{index:02d}/{len(cases):02d}] {case.case_id} "
                f"expected={result['expected_diagnosis']} "
                f"top={result['predicted_top_diagnosis'] or 'none'} "
                f"retrieval={result['retrieval_top1_label_accuracy']:.0f} "
                f"latency={result['latency_ms']:.1f}ms"
            )

        summary = {
            "system_key": system["key"],
            "system_label": system["label"],
            "description": system["description"],
            **aggregate_case_scores(case_scores),
        }
        system_results.append(summary)

    run_record: dict[str, Any] = {
        "run_id": f"benchmark-{int(time.time() * 1000)}",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": protocol,
        "encoder": encoder_name,
        "generator": generator_name,
        "systems": system_results,
    }
    run_path = Path(__file__).resolve().parent / "benchmark_runs.jsonl"
    with run_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(run_record, ensure_ascii=False) + "\n")
    return run_record


def run_benchmark_matrix(
    generator_mode: str = "synth",
    max_cases: int | None = None,
    encoder_name: str = "biomedclip",
) -> list[dict[str, Any]]:
    """Run the same real benchmark protocol as the web Evaluation tab.

    ``max_cases`` is a total count and is rounded down to a balanced number;
    for example, 32 means 16 Fractured + 16 Non_fractured cases.
    """
    modes = list(GENERATOR_MODES) if generator_mode == "all" else [generator_mode]
    unknown = [mode for mode in modes if mode not in GENERATOR_MODES]
    if unknown:
        raise ValueError(f"Generator benchmark không hợp lệ: {', '.join(unknown)}")

    cases_per_label = 16 if not max_cases else max(1, max_cases // 2)
    runs = [
        _run_generator_matrix(GENERATOR_MODES[mode], encoder_name, cases_per_label)
        for mode in modes
    ]
    return [
        {
            "run_id": run["run_id"],
            "generator": run["generator"],
            "encoder": run["encoder"],
            "protocol": run["protocol"],
            **summary,
        }
        for run in runs
        for summary in run["systems"]
    ]


def print_markdown_report(results: list[dict[str, Any]]) -> None:
    print("\n| System | Generator | Top-1 label | Evidence P@4 | Answer label | Latency | Cases |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for result in results:
        print(
            f"| {result['system_label']} | {result['generator']} | "
            f"{result['retrieval_top1_label_accuracy']:.3f} | "
            f"{result['evidence_label_precision_at_4']:.3f} | "
            f"{result['answer_label_accuracy']:.3f} | "
            f"{result['latency_ms']:.1f} ms | {result['n_cases']} |"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="BoneRAG real FracAtlas benchmark")
    parser.add_argument("--generator", choices=[*GENERATOR_MODES, "all"], default="synth")
    parser.add_argument("--encoder", choices=["biomedclip", "clip_vit_b32", "clip_vit_l14"], default="biomedclip")
    parser.add_argument("--cases", type=int, default=32, help="Total balanced cases; default: 32")
    args = parser.parse_args()

    try:
        results = run_benchmark_matrix(
            generator_mode=args.generator,
            max_cases=args.cases,
            encoder_name=args.encoder,
        )
    except (FileNotFoundError, RuntimeError, ValueError, ModuleNotFoundError, OSError) as exc:
        print(f"[benchmark] ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print_markdown_report(results)


if __name__ == "__main__":
    main()
