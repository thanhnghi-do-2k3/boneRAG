"""Paper-ready post-run evaluation for the BoneRAG benchmark.

This module does not add new benchmark systems. It takes a completed run and
adds statistical context, paired comparisons, and claim guidance so the result
can be reported honestly in a paper draft.
"""

from __future__ import annotations

import csv
import io
import math
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PAPER_METRICS: tuple[str, ...] = (
    "retrieval_top1_label_accuracy",
    "evidence_label_precision_at_4",
    "evidence_label_recall_at_4",
    "evidence_label_mrr",
    "evidence_label_ndcg_at_4",
    "answer_label_accuracy",
    "answer_factuality_score",
    "latency_ms",
)

BINARY_METRICS: set[str] = {
    "retrieval_top1_label_accuracy",
    "evidence_label_recall_at_4",
    "answer_label_accuracy",
    "answer_matches_top_evidence",
    "answer_matches_evidence_majority",
    "answer_hallucination_warning",
}

DIAGNOSTIC_METRICS: tuple[str, ...] = (
    "retrieval_sensitivity",
    "retrieval_specificity",
    "retrieval_precision",
    "retrieval_f1",
    "retrieval_balanced_accuracy",
    "answer_sensitivity",
    "answer_specificity",
    "answer_precision",
    "answer_f1",
    "answer_balanced_accuracy",
)

DISPLAY_METRICS: tuple[tuple[str, str], ...] = (
    ("retrieval_top1_label_accuracy", "Top-1 retrieval"),
    ("evidence_label_precision_at_4", "Evidence P@4"),
    ("evidence_label_mrr", "MRR"),
    ("evidence_label_ndcg_at_4", "nDCG@4"),
    ("answer_label_accuracy", "Answer accuracy"),
    ("answer_factuality_score", "Faithfulness proxy"),
)

PRIMARY_BASELINE = "image_rag"
PRIMARY_METHOD = "bonerag"
BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 1729


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _round(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def _percent(value: Any) -> str:
    number = _as_float(value)
    return f"{number * 100:.1f}%"


def _metric_is_latency(metric: str) -> bool:
    return metric.endswith("latency_ms") or metric == "latency_ms"


def _wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _bootstrap_mean_ci(values: list[float], samples: int = BOOTSTRAP_SAMPLES) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(BOOTSTRAP_SEED + len(values))
    n = len(values)
    means = []
    for _ in range(samples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    low_index = int(0.025 * (samples - 1))
    high_index = int(0.975 * (samples - 1))
    return (means[low_index], means[high_index])


def _bootstrap_delta_ci(deltas: list[float], samples: int = BOOTSTRAP_SAMPLES) -> tuple[float, float]:
    return _bootstrap_mean_ci(deltas, samples=samples)


def _mcnemar_exact_p(b: int, c: int) -> float:
    discordant = b + c
    if discordant <= 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(0, min(b, c) + 1))
    return min(1.0, 2.0 * tail / (2 ** discordant))


def _systems_from_run(run_record: dict[str, Any]) -> list[dict[str, Any]]:
    systems = run_record.get("systems")
    if isinstance(systems, list):
        return [item for item in systems if isinstance(item, dict)]
    protocol = run_record.get("protocol")
    if isinstance(protocol, dict) and isinstance(protocol.get("systems"), list):
        return [item for item in protocol["systems"] if isinstance(item, dict)]
    return []


def _cases_from_run(run_record: dict[str, Any]) -> list[dict[str, Any]]:
    cases = run_record.get("cases")
    return [item for item in cases if isinstance(item, dict)] if isinstance(cases, list) else []


def _protocol_from_run(run_record: dict[str, Any]) -> dict[str, Any]:
    protocol = run_record.get("protocol")
    return protocol if isinstance(protocol, dict) else {}


def _case_rows_by_system(cases: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in cases:
        key = str(item.get("system_key", "")).strip()
        if key:
            grouped[key].append(item)
    return grouped


def _values(rows: list[dict[str, Any]], metric: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        if metric in row and row.get(metric) is not None:
            values.append(_as_float(row.get(metric)))
    return values


def _diagnostic_counts(rows: list[dict[str, Any]], prediction_key: str) -> dict[str, int]:
    tp = tn = fp = fn = unknown = 0
    for item in rows:
        expected = item.get("expected_diagnosis")
        predicted = item.get(prediction_key)
        if expected == "fracture":
            if predicted == "fracture":
                tp += 1
            elif predicted == "normal":
                fn += 1
            else:
                unknown += 1
                fn += 1
        elif expected == "normal":
            if predicted == "normal":
                tn += 1
            elif predicted == "fracture":
                fp += 1
            else:
                unknown += 1
                fp += 1
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn, "unknown": unknown}


def _diagnostic_metrics_from_counts(counts: dict[str, int]) -> dict[str, float]:
    tp = counts["tp"]
    tn = counts["tn"]
    fp = counts["fp"]
    fn = counts["fn"]
    positives = tp + fn
    negatives = tn + fp
    sensitivity = tp / positives if positives else 0.0
    specificity = tn / negatives if negatives else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * precision * sensitivity / (precision + sensitivity)) if (precision + sensitivity) else 0.0
    balanced_accuracy = (sensitivity + specificity) / 2 if (positives or negatives) else 0.0
    return {
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f1": f1,
        "balanced_accuracy": balanced_accuracy,
    }


def _diagnostic_bootstrap_ci(rows: list[dict[str, Any]], prediction_key: str, metric: str) -> tuple[float, float]:
    if not rows:
        return (0.0, 0.0)
    if len(rows) == 1:
        counts = _diagnostic_counts(rows, prediction_key)
        value = _diagnostic_metrics_from_counts(counts)[metric]
        return (value, value)
    rng = random.Random(BOOTSTRAP_SEED + len(rows) + len(metric))
    n = len(rows)
    values: list[float] = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [rows[rng.randrange(n)] for _ in range(n)]
        counts = _diagnostic_counts(sample, prediction_key)
        values.append(_diagnostic_metrics_from_counts(counts)[metric])
    values.sort()
    return (values[int(0.025 * (BOOTSTRAP_SAMPLES - 1))], values[int(0.975 * (BOOTSTRAP_SAMPLES - 1))])


def _metric_entry(rows: list[dict[str, Any]], summary: dict[str, Any], metric: str) -> dict[str, Any]:
    values = _values(rows, metric)
    n = len(values)
    summary_value = summary.get(metric)
    mean_value = _mean(values) if values else (_as_float(summary_value) if summary_value is not None else None)
    entry: dict[str, Any] = {
        "mean": _round(mean_value),
        "n": n,
        "ci95": None,
        "ci_method": None,
    }
    if values:
        if metric in BINARY_METRICS:
            successes = sum(1 for value in values if value >= 0.5)
            low, high = _wilson_ci(successes, n)
            entry.update({
                "successes": successes,
                "ci95": [_round(low), _round(high)],
                "ci_method": "Wilson score interval",
            })
        else:
            low, high = _bootstrap_mean_ci(values)
            entry.update({
                "ci95": [_round(low), _round(high)],
                "ci_method": "paired case bootstrap" if metric == "latency_ms" else "case bootstrap",
            })
    return entry


def _diagnostic_metric_entries(rows: list[dict[str, Any]], prefix: str) -> dict[str, dict[str, Any]]:
    prediction_key = "predicted_top_diagnosis" if prefix == "retrieval" else "answer_predicted_diagnosis"
    counts = _diagnostic_counts(rows, prediction_key)
    metrics = _diagnostic_metrics_from_counts(counts)
    entries: dict[str, dict[str, Any]] = {}
    for metric_name, value in metrics.items():
        low, high = _diagnostic_bootstrap_ci(rows, prediction_key, metric_name)
        entries[f"{prefix}_{metric_name}"] = {
            "mean": _round(value),
            "n": len(rows),
            "ci95": [_round(low), _round(high)],
            "ci_method": "case bootstrap",
        }
    return entries


def _paired_rows(
    grouped: dict[str, list[dict[str, Any]]],
    baseline_key: str,
    method_key: str,
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    baseline_by_case = {str(item.get("case_id")): item for item in grouped.get(baseline_key, [])}
    method_by_case = {str(item.get("case_id")): item for item in grouped.get(method_key, [])}
    shared = sorted(set(baseline_by_case) & set(method_by_case))
    return {case_id: (baseline_by_case[case_id], method_by_case[case_id]) for case_id in shared}


def _claim_direction(metric: str, delta: float, low: float, high: float) -> str:
    if low <= 0.0 <= high:
        return "inconclusive"
    if _metric_is_latency(metric):
        return "improved" if delta < 0 else "degraded"
    return "improved" if delta > 0 else "degraded"


def _paired_comparison(
    grouped: dict[str, list[dict[str, Any]]],
    systems_by_key: dict[str, dict[str, Any]],
    baseline_key: str = PRIMARY_BASELINE,
    method_key: str = PRIMARY_METHOD,
) -> list[dict[str, Any]]:
    shared_rows = _paired_rows(grouped, baseline_key, method_key)
    if not shared_rows:
        return []
    comparisons: list[dict[str, Any]] = []
    for metric in PAPER_METRICS:
        deltas: list[float] = []
        baseline_values: list[float] = []
        method_values: list[float] = []
        b = c = 0
        for baseline_row, method_row in shared_rows.values():
            if metric not in baseline_row or metric not in method_row:
                continue
            baseline_value = _as_float(baseline_row.get(metric))
            method_value = _as_float(method_row.get(metric))
            baseline_values.append(baseline_value)
            method_values.append(method_value)
            deltas.append(method_value - baseline_value)
            if metric in BINARY_METRICS:
                baseline_ok = baseline_value >= 0.5
                method_ok = method_value >= 0.5
                if method_ok and not baseline_ok:
                    b += 1
                elif baseline_ok and not method_ok:
                    c += 1
        if not deltas:
            continue
        low, high = _bootstrap_delta_ci(deltas)
        delta = _mean(deltas) or 0.0
        comparison = {
            "baseline_system_key": baseline_key,
            "baseline_system_label": systems_by_key.get(baseline_key, {}).get("system_label", baseline_key),
            "method_system_key": method_key,
            "method_system_label": systems_by_key.get(method_key, {}).get("system_label", method_key),
            "metric": metric,
            "n_paired_cases": len(deltas),
            "baseline_mean": _round(_mean(baseline_values)),
            "method_mean": _round(_mean(method_values)),
            "delta": _round(delta),
            "delta_ci95": [_round(low), _round(high)],
            "delta_ci_method": "paired case bootstrap",
            "claim_direction": _claim_direction(metric, delta, low, high),
        }
        if metric in BINARY_METRICS:
            comparison.update({
                "mcnemar_b_method_correct_only": b,
                "mcnemar_c_baseline_correct_only": c,
                "mcnemar_exact_p": _round(_mcnemar_exact_p(b, c)),
            })
        comparisons.append(comparison)
    return comparisons


def _error_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    retrieval_counts = _diagnostic_counts(rows, "predicted_top_diagnosis")
    answer_counts = _diagnostic_counts(rows, "answer_predicted_diagnosis")
    evidence_ties = sum(1 for row in rows if not row.get("evidence_majority_diagnosis"))
    unsupported_claims = sum(int(_as_float(row.get("answer_unsupported_claims", 0))) for row in rows)
    hallucination_warnings = sum(1 for row in rows if bool(row.get("answer_hallucination_warning")))
    return {
        "retrieval": retrieval_counts,
        "answer": answer_counts,
        "evidence_majority_ties": evidence_ties,
        "answer_unsupported_claims": unsupported_claims,
        "answer_hallucination_warnings": hallucination_warnings,
    }


def _allowed_and_blocked_claims(
    protocol: dict[str, Any],
    systems: list[dict[str, Any]],
    paired: list[dict[str, Any]],
) -> dict[str, list[str]]:
    n_cases = int(_as_float(protocol.get("n_cases", 0)))
    official_repro = bool(protocol.get("official_paper_reproductions"))
    has_vqa_gt = bool(protocol.get("vqa_explanation_ground_truth"))
    test_holdout = bool(protocol.get("test_holdout")) and bool(protocol.get("test_ids_excluded_from_retrieval"))
    fallback_systems = [
        system.get("system_label", system.get("system_key", "unknown"))
        for system in systems
        if _as_float(system.get("generator_fallback_rate", 0.0)) > 0
    ]
    allowed = [
        "Report this as an internal FracAtlas binary image-retrieval/classification ablation with the recorded fingerprint.",
        "Compare BoneRAG only against systems actually executed on the same cases, encoder, generator, and hold-out protocol.",
    ]
    blocked = [
        "Do not claim superiority over MMed-RAG, RULE, FactMM-RAG, MR-RAG, MKGF, Path-RAG, or VisRAG without running their real method/checkpoint on a shared benchmark.",
        "Do not claim clinical explanation quality from this run; the current task has no radiologist reference rationale.",
    ]
    warnings: list[str] = []

    if not test_holdout:
        blocked.append("Do not publish the run until test query images are excluded from retrieval.")
    if n_cases < 64:
        warnings.append("Case count is small for a paper table; use at least 64/128 balanced cases and report the fingerprint.")
    if fallback_systems:
        blocked.append(
            "Do not report neural-generator results while generator_fallback_rate is non-zero for: "
            + ", ".join(str(name) for name in fallback_systems)
        )
    if not official_repro:
        warnings.append("Published paper methods are discussion baselines only in this run, not direct numerical comparators.")
    if not has_vqa_gt:
        warnings.append("Answer metrics are binary label proxies; use VQA-RAD/SLAKE/etc. for real VQA claims.")

    top1 = next((item for item in paired if item.get("metric") == "retrieval_top1_label_accuracy"), None)
    p4 = next((item for item in paired if item.get("metric") == "evidence_label_precision_at_4"), None)
    answer = next((item for item in paired if item.get("metric") == "answer_label_accuracy"), None)
    if top1 and top1.get("claim_direction") == "improved":
        allowed.append("A paired improvement claim is supportable for retrieval Top-1 on this run.")
    elif top1:
        warnings.append("Retrieval Top-1 does not show a statistically clear BoneRAG improvement over Image-only in this run.")
    if p4 and p4.get("claim_direction") == "improved":
        allowed.append("A paired improvement claim is supportable for Evidence P@4 on this run.")
    if answer and answer.get("claim_direction") == "improved":
        allowed.append("A paired improvement claim is supportable for binary answer label accuracy on this run.")

    return {"allowed": allowed, "warnings": warnings, "blocked": blocked}


def build_paper_evaluation(run_record: dict[str, Any]) -> dict[str, Any]:
    """Build a paper-oriented evaluation artifact from one completed benchmark run."""
    systems = _systems_from_run(run_record)
    cases = _cases_from_run(run_record)
    protocol = _protocol_from_run(run_record)
    grouped = _case_rows_by_system(cases)
    systems_by_key = {
        str(system.get("system_key", "")): system
        for system in systems
        if str(system.get("system_key", "")).strip()
    }

    system_cards: list[dict[str, Any]] = []
    for system in systems:
        key = str(system.get("system_key", "")).strip()
        rows = grouped.get(key, [])
        metrics: dict[str, dict[str, Any]] = {}
        for metric in PAPER_METRICS:
            metrics[metric] = _metric_entry(rows, system, metric)
        if rows:
            metrics.update(_diagnostic_metric_entries(rows, "retrieval"))
            metrics.update(_diagnostic_metric_entries(rows, "answer"))
        else:
            for metric in DIAGNOSTIC_METRICS:
                if metric in system:
                    metrics[metric] = {
                        "mean": _round(_as_float(system.get(metric))),
                        "n": 0,
                        "ci95": None,
                        "ci_method": None,
                    }
        system_cards.append({
            "system_key": key,
            "system_label": system.get("system_label", key),
            "n_cases": int(_as_float(system.get("n_cases", len(rows)))),
            "metrics": metrics,
            "error_breakdown": _error_breakdown(rows),
        })

    paired = _paired_comparison(grouped, systems_by_key)
    claims = _allowed_and_blocked_claims(protocol, systems, paired)
    return {
        "schema_version": "paper-eval-v1",
        "run_id": run_record.get("run_id"),
        "benchmark_version": protocol.get("benchmark_version"),
        "dataset_fingerprint": protocol.get("dataset_fingerprint"),
        "n_cases": protocol.get("n_cases") or (len(cases) // max(1, len(systems) or 1)),
        "statistical_methods": {
            "system_metric_ci": "Wilson interval for binary metrics; nonparametric case bootstrap for continuous means and diagnostic metrics.",
            "paired_delta_ci": "Paired nonparametric bootstrap over shared case IDs.",
            "paired_binary_test": "Exact two-sided McNemar/binomial test on discordant case pairs.",
            "bootstrap_samples": BOOTSTRAP_SAMPLES,
        },
        "systems": system_cards,
        "paired_comparisons": paired,
        "claim_guidance": claims,
    }


def _metric_cell(card: dict[str, Any], metric: str, as_percent: bool = True) -> str:
    entry = card.get("metrics", {}).get(metric, {})
    value = entry.get("mean")
    if value is None:
        return "-"
    if _metric_is_latency(metric):
        text = f"{_as_float(value):.1f} ms"
    elif as_percent:
        text = _percent(value)
    else:
        text = f"{_as_float(value):.3f}"
    ci = entry.get("ci95")
    if isinstance(ci, list) and len(ci) == 2:
        if _metric_is_latency(metric):
            text += f" [{_as_float(ci[0]):.1f}, {_as_float(ci[1]):.1f}]"
        elif as_percent:
            text += f" [{_percent(ci[0])}, {_percent(ci[1])}]"
        else:
            text += f" [{_as_float(ci[0]):.3f}, {_as_float(ci[1]):.3f}]"
    return text


def build_markdown_report(run_record: dict[str, Any]) -> str:
    paper = run_record.get("paper_evaluation")
    if not isinstance(paper, dict):
        paper = build_paper_evaluation(run_record)
    protocol = _protocol_from_run(run_record)
    lines = [
        "# BoneRAG Benchmark Paper Evaluation",
        "",
        f"- Run ID: `{run_record.get('run_id', '-')}`",
        f"- Created at: `{run_record.get('created_at', '-')}`",
        f"- Protocol: `{protocol.get('benchmark_version', paper.get('benchmark_version', '-'))}`",
        f"- Dataset fingerprint: `{protocol.get('dataset_fingerprint', paper.get('dataset_fingerprint', '-'))}`",
        f"- Cases: `{protocol.get('n_cases', paper.get('n_cases', '-'))}`",
        f"- Encoder / generator: `{run_record.get('encoder', '-')}` / `{run_record.get('generator', '-')}`",
        "",
        "## System Metrics",
        "",
        "| System | Top-1 retrieval | Evidence P@4 | Retrieval F1 | Sens / Spec | Answer accuracy | Answer F1 | Faithfulness proxy | Latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for card in paper.get("systems", []):
        lines.append(
            "| "
            + " | ".join([
                str(card.get("system_label", card.get("system_key", "-"))),
                _metric_cell(card, "retrieval_top1_label_accuracy"),
                _metric_cell(card, "evidence_label_precision_at_4"),
                _metric_cell(card, "retrieval_f1"),
                f"{_metric_cell(card, 'retrieval_sensitivity')} / {_metric_cell(card, 'retrieval_specificity')}",
                _metric_cell(card, "answer_label_accuracy"),
                _metric_cell(card, "answer_f1"),
                _metric_cell(card, "answer_factuality_score"),
                _metric_cell(card, "latency_ms", as_percent=False),
            ])
            + " |"
        )

    lines.extend([
        "",
        "## Paired BoneRAG vs Image-only",
        "",
        "| Metric | Image-only | BoneRAG | Delta | 95% CI | McNemar p | Direction |",
        "|---|---:|---:|---:|---:|---:|---|",
    ])
    for item in paper.get("paired_comparisons", []):
        metric = str(item.get("metric", "-"))
        ci = item.get("delta_ci95") or [None, None]
        p_value = item.get("mcnemar_exact_p")
        formatter = (lambda v: f"{_as_float(v):.1f} ms") if _metric_is_latency(metric) else _percent
        delta_text = f"{_as_float(item.get('delta')):.1f} ms" if _metric_is_latency(metric) else _percent(item.get("delta"))
        ci_text = (
            f"[{_as_float(ci[0]):.1f}, {_as_float(ci[1]):.1f}]"
            if _metric_is_latency(metric)
            else f"[{_percent(ci[0])}, {_percent(ci[1])}]"
        )
        p_text = f"{_as_float(p_value):.4f}" if p_value is not None else "-"
        lines.append(
            f"| `{metric}` | {formatter(item.get('baseline_mean'))} | "
            f"{formatter(item.get('method_mean'))} | {delta_text} | {ci_text} | "
            f"{p_text} | {item.get('claim_direction', '-')} |"
        )
    if not paper.get("paired_comparisons"):
        lines.append("| - | - | - | - | - | - | No paired comparison available |")

    claims = paper.get("claim_guidance", {})
    lines.extend(["", "## Claim Guidance", "", "Allowed:"])
    lines.extend(f"- {text}" for text in claims.get("allowed", []))
    lines.append("")
    lines.append("Warnings:")
    lines.extend(f"- {text}" for text in claims.get("warnings", []))
    lines.append("")
    lines.append("Blocked:")
    lines.extend(f"- {text}" for text in claims.get("blocked", []))
    lines.append("")
    return "\n".join(lines)


def build_systems_csv(run_record: dict[str, Any]) -> str:
    paper = run_record.get("paper_evaluation")
    if not isinstance(paper, dict):
        paper = build_paper_evaluation(run_record)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "system_key",
        "system_label",
        "metric",
        "mean",
        "ci95_low",
        "ci95_high",
        "ci_method",
        "n",
    ])
    for card in paper.get("systems", []):
        for metric, entry in card.get("metrics", {}).items():
            ci = entry.get("ci95") if isinstance(entry, dict) else None
            writer.writerow([
                card.get("system_key"),
                card.get("system_label"),
                metric,
                entry.get("mean") if isinstance(entry, dict) else None,
                ci[0] if isinstance(ci, list) and len(ci) == 2 else None,
                ci[1] if isinstance(ci, list) and len(ci) == 2 else None,
                entry.get("ci_method") if isinstance(entry, dict) else None,
                entry.get("n") if isinstance(entry, dict) else None,
            ])
    return output.getvalue()


def build_paired_comparisons_csv(run_record: dict[str, Any]) -> str:
    paper = run_record.get("paper_evaluation")
    if not isinstance(paper, dict):
        paper = build_paper_evaluation(run_record)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "metric",
        "baseline_system_key",
        "method_system_key",
        "n_paired_cases",
        "baseline_mean",
        "method_mean",
        "delta",
        "delta_ci95_low",
        "delta_ci95_high",
        "mcnemar_b_method_correct_only",
        "mcnemar_c_baseline_correct_only",
        "mcnemar_exact_p",
        "claim_direction",
    ])
    writer.writeheader()
    for item in paper.get("paired_comparisons", []):
        ci = item.get("delta_ci95") or [None, None]
        writer.writerow({
            "metric": item.get("metric"),
            "baseline_system_key": item.get("baseline_system_key"),
            "method_system_key": item.get("method_system_key"),
            "n_paired_cases": item.get("n_paired_cases"),
            "baseline_mean": item.get("baseline_mean"),
            "method_mean": item.get("method_mean"),
            "delta": item.get("delta"),
            "delta_ci95_low": ci[0],
            "delta_ci95_high": ci[1],
            "mcnemar_b_method_correct_only": item.get("mcnemar_b_method_correct_only"),
            "mcnemar_c_baseline_correct_only": item.get("mcnemar_c_baseline_correct_only"),
            "mcnemar_exact_p": item.get("mcnemar_exact_p"),
            "claim_direction": item.get("claim_direction"),
        })
    return output.getvalue()


def build_case_audit_csv(run_record: dict[str, Any]) -> str:
    rows = _cases_from_run(run_record)
    output = io.StringIO()
    fieldnames = [
        "case_id",
        "query_image_id",
        "system_key",
        "expected_diagnosis",
        "predicted_top_diagnosis",
        "evidence_majority_diagnosis",
        "answer_predicted_diagnosis",
        "retrieval_top1_label_accuracy",
        "evidence_label_precision_at_4",
        "evidence_label_mrr",
        "evidence_label_ndcg_at_4",
        "answer_label_accuracy",
        "answer_factuality_score",
        "latency_ms",
        "top_evidence_id",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key) for key in fieldnames})
    return output.getvalue()


def build_summary_svg(run_record: dict[str, Any]) -> str:
    paper = run_record.get("paper_evaluation")
    if not isinstance(paper, dict):
        paper = build_paper_evaluation(run_record)
    systems = paper.get("systems", [])
    width = 980
    row_height = 26
    metric_gap = 28
    left = 210
    top = 56
    bar_width = 130
    height = top + len(DISPLAY_METRICS) * (len(systems) * row_height + metric_gap) + 32
    palette = ["#14b8a6", "#38bdf8", "#f59e0b", "#a78bfa", "#f97316", "#22c55e"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#111"/>',
        '<text x="24" y="32" fill="#f5f5f5" font-family="Arial, sans-serif" font-size="18" font-weight="700">BoneRAG paper evaluation summary</text>',
        f'<text x="24" y="50" fill="#aaa" font-family="Arial, sans-serif" font-size="12">Fingerprint: {paper.get("dataset_fingerprint", "-")} | cases: {paper.get("n_cases", "-")}</text>',
    ]
    y = top
    for metric_index, (metric, label) in enumerate(DISPLAY_METRICS):
        parts.append(f'<text x="24" y="{y + 16}" fill="#ddd" font-family="Arial, sans-serif" font-size="13" font-weight="700">{label}</text>')
        for system_index, card in enumerate(systems):
            entry = card.get("metrics", {}).get(metric, {})
            value = max(0.0, min(1.0, _as_float(entry.get("mean", 0.0))))
            row_y = y + 24 + system_index * row_height
            color = palette[system_index % len(palette)]
            label_text = str(card.get("system_label", card.get("system_key", "-")))
            label_text = re.sub(r"[<>&]", "", label_text)
            parts.extend([
                f'<text x="{left - 8}" y="{row_y + 13}" fill="#bbb" font-family="Arial, sans-serif" font-size="12" text-anchor="end">{label_text}</text>',
                f'<rect x="{left}" y="{row_y}" width="{bar_width}" height="14" rx="4" fill="#333"/>',
                f'<rect x="{left}" y="{row_y}" width="{max(2, value * bar_width):.1f}" height="14" rx="4" fill="{color}"/>',
                f'<text x="{left + bar_width + 10}" y="{row_y + 13}" fill="#eee" font-family="Arial, sans-serif" font-size="12">{_percent(value)}</text>',
            ])
        y += len(systems) * row_height + metric_gap
    parts.append("</svg>")
    return "\n".join(parts)


def build_artifact_bundle(run_record: dict[str, Any]) -> dict[str, str]:
    enriched = dict(run_record)
    enriched["paper_evaluation"] = build_paper_evaluation(run_record)
    return {
        "markdown_report": build_markdown_report(enriched),
        "systems_csv": build_systems_csv(enriched),
        "paired_comparisons_csv": build_paired_comparisons_csv(enriched),
        "case_audit_csv": build_case_audit_csv(enriched),
        "summary_svg": build_summary_svg(enriched),
    }


def write_artifact_bundle(run_record: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)
    bundle = build_artifact_bundle(run_record)
    file_map = {
        "markdown_report": "paper_evaluation_report.md",
        "systems_csv": "paper_system_metrics.csv",
        "paired_comparisons_csv": "paper_paired_comparisons.csv",
        "case_audit_csv": "paper_case_audit.csv",
        "summary_svg": "paper_summary_chart.svg",
    }
    written: dict[str, str] = {}
    for key, filename in file_map.items():
        path = output_path / filename
        path.write_text(bundle[key], encoding="utf-8")
        written[key] = str(path)
    return written
