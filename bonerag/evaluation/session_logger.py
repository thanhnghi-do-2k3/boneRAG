"""Research Session Logger for BoneRAG.

Appends structured Q&A session entries to a JSONL file for research analysis.
Each line is an independent JSON object (append-friendly, Pandas-readable).
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_LOG_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "sessions.jsonl"


class SessionLogger:
    """Thread-safe logger that appends session entries to a JSONL file."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        self.log_path = Path(log_path) if log_path else _DEFAULT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log(self, entry: dict) -> None:
        """Append a session entry to the JSONL file (thread-safe)."""
        entry.setdefault("timestamp_iso", datetime.now(timezone.utc).isoformat())
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def update_feedback(self, session_id: str, rating: int) -> bool:
        """Update user_feedback field for a given session_id (rewrite file).

        Returns True if the session was found and updated.
        """
        with self._lock:
            entries = self._read_all()
            updated = False
            for entry in entries:
                if entry.get("session_id") == session_id:
                    entry["user_feedback"] = rating
                    updated = True
            if updated:
                with self.log_path.open("w", encoding="utf-8") as fh:
                    for e in entries:
                        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            return updated

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_all(self) -> list[dict]:
        """Return all session log entries as a list of dicts."""
        with self._lock:
            return self._read_all()

    def _read_all(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        entries = []
        with self.log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    # ------------------------------------------------------------------
    # Build entry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_entry(
        *,
        session_id: str,
        question_raw: str,
        question_pipeline: str,
        model_config: dict,
        attached_image: dict | None,
        retrieval: dict,
        evidence: list[dict],
        answer: str,
        latency_ms: int,
        eval_scores: dict | None = None,
    ) -> dict:
        """Build a structured session log entry."""
        return {
            "session_id": session_id,
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "question_raw": question_raw,
            "question_pipeline": question_pipeline,
            "model_config": model_config,
            "attached_image": attached_image,
            "retrieval": retrieval,
            "evidence": evidence,
            "answer": answer,
            "latency_ms": latency_ms,
            "eval_scores": eval_scores or {},
            "user_feedback": None,
        }
