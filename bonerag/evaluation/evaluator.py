"""BoneRAG Evaluation Framework.

Computes RAG evaluation metrics from session logs:
- recall_at_k: Was the expected evidence in top-K hits?
- mrr: Mean Reciprocal Rank of expected evidence
- answer_label_accuracy: Did the answer mention the correct diagnosis label?
- faithfulness_score: Fraction of evidence IDs mentioned in the answer
- latency_ms: Captured from session log
- context_relevance: Average cosine similarity of retrieved hits

Usage:
    python3 -m bonerag.evaluation.evaluator --log bonerag/evaluation/sessions.jsonl
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_GT_PATH = Path(__file__).resolve().parent / "ground_truth.json"
_SESSIONS_PATH = Path(__file__).resolve().parent / "sessions.jsonl"


class BoneRAGEvaluator:
    """Compute evaluation metrics for BoneRAG pipeline sessions."""

    def __init__(self, ground_truth_path: Path | str | None = None) -> None:
        gt_path = Path(ground_truth_path) if ground_truth_path else _GT_PATH
        self.ground_truth: list[dict] = []
        if gt_path.exists():
            with gt_path.open("r", encoding="utf-8") as fh:
                self.ground_truth = json.load(fh)
        # Build lookup by question prefix for fast matching
        self._gt_index: dict[str, dict] = {
            entry["question"].lower(): entry for entry in self.ground_truth
        }

    # ------------------------------------------------------------------
    # Core metric functions
    # ------------------------------------------------------------------

    def recall_at_k(self, session: dict, k: int = 4) -> float | None:
        """1.0 if any expected evidence ID is in the top-K retrieved hits."""
        gt = self._match_ground_truth(session.get("question_raw", ""))
        if gt is None:
            return None
        expected_ids = set(gt.get("expected_evidence_ids", []))
        hits: list[dict] = (session.get("retrieval") or {}).get("hits", [])[:k]
        hit_ids = {h.get("record_id", "") for h in hits}
        return 1.0 if expected_ids & hit_ids else 0.0

    def mrr(self, session: dict) -> float | None:
        """Mean Reciprocal Rank: 1/rank of first correct hit."""
        gt = self._match_ground_truth(session.get("question_raw", ""))
        if gt is None:
            return None
        expected_ids = set(gt.get("expected_evidence_ids", []))
        hits: list[dict] = (session.get("retrieval") or {}).get("hits", [])
        for rank, hit in enumerate(hits, start=1):
            if hit.get("record_id", "") in expected_ids:
                return 1.0 / rank
        return 0.0

    def answer_label_accuracy(self, session: dict) -> float | None:
        """1.0 if expected diagnosis label appears in the answer text."""
        gt = self._match_ground_truth(session.get("question_raw", ""))
        if gt is None:
            return None
        expected_label = gt.get("expected_diagnosis", "").lower()
        answer = (session.get("answer") or "").lower()
        return 1.0 if expected_label and expected_label in answer else 0.0

    def faithfulness_score(self, session: dict) -> float:
        """Fraction of retrieved evidence IDs mentioned in the answer."""
        evidence: list[dict] = session.get("evidence") or []
        answer = (session.get("answer") or "").lower()
        if not evidence:
            return 0.0
        mentioned = sum(
            1 for e in evidence if (e.get("image_id") or "").lower() in answer
        )
        return mentioned / len(evidence)

    def context_relevance(self, session: dict) -> float:
        """Average rerank score of retrieved evidence (proxy for relevance)."""
        evidence: list[dict] = session.get("evidence") or []
        if not evidence:
            return 0.0
        scores = [e.get("rerank_score", 0.0) for e in evidence]
        return sum(scores) / len(scores)

    # ------------------------------------------------------------------
    # Combined scoring
    # ------------------------------------------------------------------

    def score_session(self, session: dict) -> dict[str, Any]:
        """Return all metrics for a single session log entry."""
        return {
            "recall_at_4": self.recall_at_k(session, k=4),
            "mrr": self.mrr(session),
            "answer_label_accuracy": self.answer_label_accuracy(session),
            "faithfulness_score": self.faithfulness_score(session),
            "context_relevance": self.context_relevance(session),
            "latency_ms": session.get("latency_ms"),
        }

    def score_all(self, sessions: list[dict]) -> list[dict]:
        """Score every session and return enriched entries."""
        result = []
        for s in sessions:
            scores = self.score_session(s)
            result.append({**s, "eval_scores": scores})
        return result

    def aggregate(self, sessions: list[dict]) -> dict[str, Any]:
        """Compute macro-averages across all sessions with non-null values."""
        scored = self.score_all(sessions)
        keys = ["recall_at_4", "mrr", "answer_label_accuracy", "faithfulness_score",
                "context_relevance", "latency_ms"]
        agg: dict[str, Any] = {}
        for key in keys:
            values = [s["eval_scores"].get(key) for s in scored if s["eval_scores"].get(key) is not None]
            agg[key] = round(sum(values) / len(values), 4) if values else None
        agg["n_sessions"] = len(sessions)
        return agg

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _match_ground_truth(self, question_raw: str) -> dict | None:
        q = question_raw.lower().strip()
        # Exact
        if q in self._gt_index:
            return self._gt_index[q]
        # Substring match
        for gt_q, entry in self._gt_index.items():
            if gt_q in q or q in gt_q:
                return entry
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="BoneRAG Evaluator CLI")
    parser.add_argument("--log", default=str(_SESSIONS_PATH), help="Path to sessions.jsonl")
    parser.add_argument("--gt", default=str(_GT_PATH), help="Path to ground_truth.json")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        print(f"[evaluator] sessions log not found: {log_path}")
        return

    sessions: list[dict] = []
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    sessions.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    evaluator = BoneRAGEvaluator(ground_truth_path=args.gt)
    agg = evaluator.aggregate(sessions)

    if args.format == "json":
        print(json.dumps(agg, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*50}")
        print(f"  BoneRAG Evaluation Report — {len(sessions)} sessions")
        print(f"{'='*50}")
        for k, v in agg.items():
            if k == "n_sessions":
                continue
            val_str = f"{v:.4f}" if isinstance(v, float) else str(v)
            print(f"  {k:<30} {val_str}")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    _cli()
