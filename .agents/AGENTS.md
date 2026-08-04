# AGENTS.md - Workspace Agent Guidelines & Context

## Quick Overview
Project **BoneRAG**: Medical Visual Question Answering (VQA) for bone pathology & fracture detection using Image-based RAG.

- Core Algorithm: `bonerag/main_algo` (`data.py`, `encoder.py`, `vector_index.py`, `pipeline.py`).
- Demo Server: `demo-app/server.py` (Python stdlib HTTP + SSE on port 8088).
- Demo Frontend: `demo-app/frontend` (React + Vite).
- Research Hub: `research-server` (Vite dev server on port 5173).

For complete function signatures, data schemas, and architecture map, see [.agents/CODEBASE_MAP.md](file://.agents/CODEBASE_MAP.md).

## Token Efficiency & Audit Rules
1. Refer to [.agents/CODEBASE_MAP.md](file://.agents/CODEBASE_MAP.md) before performing redundant codebase research.
2. Keep `.gitignore` rules intact (`node_modules/`, `.venv/`, `dist/`, `__pycache__/`).
3. Always verify changes using unit tests: `python3 -m unittest discover -s bonerag/tests`.
4. **Self-Correction Audit Logging**: Whenever the Agent identifies a bug or makes a code fix/refactoring, append a structured log entry to [agent_corrections.md](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/algorithm-logs/agent_corrections.md) with Timestamp, Reason for Fix, Root Cause, Changes Applied, and Outcome.
