"""HTTP server for the BoneRAG demo app.

Run from the repository root:

    python3 demo-app/server.py --port 8088

Milestone 3 routes:
- GET  /api/records           — image library
- GET  /api/image/<id>        — serve image file
- GET  /api/answer-stream     — SSE streaming Q&A
- GET  /api/model-configs     — list available encoders & generators
- GET  /api/sessions          — research session logs
- POST /api/set-config        — switch active model config (saves Gemini API key)
- POST /api/feedback          — user thumbs up/down for a session
- POST /api/answer            — synchronous Q&A (legacy)
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1] / "bonerag"))

from main_algo.encoder import get_multimodal_encoder, AVAILABLE_ENCODERS
from main_algo.generator import get_generator, AVAILABLE_GENERATORS
from main_algo.pipeline import BoneRAGPipeline
from evaluation.session_logger import SessionLogger
from evaluation.evaluator import BoneRAGEvaluator

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
FRONTEND_DIST = ROOT / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Global state — pipeline cache + session logger
# ---------------------------------------------------------------------------

_PIPELINE_CACHE: dict[str, BoneRAGPipeline] = {}
_ACTIVE_CONFIG: dict = {
    "encoder": "hashing",
    "generator": "template",
    "gemini_api_key": "",
    "gemini_model": "gemini-1.5-flash",
    "top_k": 4,
    "min_similarity": 0.02,
}

SESSION_LOGGER = SessionLogger()
EVALUATOR = BoneRAGEvaluator()


def _pipeline_cache_key(config: dict) -> str:
    return f"{config['encoder']}|{config['generator']}|{config.get('gemini_model', '')}|{config['top_k']}|{config['min_similarity']}"


def _get_pipeline(config: dict | None = None) -> BoneRAGPipeline:
    """Return a cached pipeline for the given config, or for ACTIVE_CONFIG."""
    cfg = config or _ACTIVE_CONFIG
    key = _pipeline_cache_key(cfg)
    if key not in _PIPELINE_CACHE:
        encoder = get_multimodal_encoder(mode=cfg.get("encoder", "hashing"))
        gen_name = cfg.get("generator", "template")
        gen_kwargs: dict = {}
        if gen_name == "gemini":
            gen_kwargs["api_key"] = cfg.get("gemini_api_key", "")
            gen_kwargs["model"] = cfg.get("gemini_model", "gemini-1.5-flash")
        generator = get_generator(gen_name, **gen_kwargs)
        _PIPELINE_CACHE[key] = BoneRAGPipeline(
            encoder=encoder,
            generator=generator,
            top_k=int(cfg.get("top_k", 4)),
            min_similarity=float(cfg.get("min_similarity", 0.02)),
        )
    return _PIPELINE_CACHE[key]


# Initialise default pipeline eagerly at startup
_get_pipeline()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class BoneRAGHandler(BaseHTTPRequestHandler):
    server_version = "BoneRAGDemo/0.2"

    def log_message(self, format: str, *args) -> None:
        print(f"[demo-app] {self.address_string()} - {format % args}")

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    def _send_json(self, payload: dict | list, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "not found"}, status=404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_sse(self, events) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        for event in events:
            raw = f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(raw)
            self.wfile.flush()
            time.sleep(0.02)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ------------------------------------------------------------------
    # Payload transformers
    # ------------------------------------------------------------------

    def _record_to_public_payload(self, record: dict) -> dict:
        payload = dict(record)
        image_id = str(payload.get("image_id", "")).strip()
        image_path = str(payload.get("image_path", "")).strip()
        if image_id and image_path:
            payload["image_url"] = f"/api/image/{quote(image_id, safe='')}"
        else:
            payload["image_url"] = None
        return payload

    def _result_to_public_payload(self, result: dict) -> dict:
        payload = dict(result)
        evidence = payload.get("evidence", [])
        if isinstance(evidence, list):
            payload["evidence"] = [
                self._record_to_public_payload(item) if isinstance(item, dict) else item
                for item in evidence
            ]
        return payload

    def _send_record_image(self, image_id: str) -> None:
        pipeline = _get_pipeline()
        record = pipeline.record_by_id.get(image_id)
        if not record or not record.image_path:
            self._send_json({"error": "image not found"}, status=404)
            return
        image_path = Path(record.image_path).expanduser().resolve()
        if not image_path.exists() or not image_path.is_file():
            self._send_json({"error": "image file missing"}, status=404)
            return
        self._send_file(image_path)

    def _public_stream_events(self, events, session_id: str, question_raw: str, question_pipeline: str, attached_image: dict | None):
        """Wrap raw pipeline events: transform done payload and log the session."""
        start_time = time.monotonic()
        collected_hits: list = []
        collected_evidence: list = []
        final_answer: str = ""
        final_result: dict = {}
        used_retrieval: bool = False

        for event in events:
            if not isinstance(event, dict):
                yield event
                continue

            if event.get("type") == "stage" and "hits" in event:
                collected_hits = event.get("hits", [])

            if event.get("type") == "done" and isinstance(event.get("result"), dict):
                public_result = self._result_to_public_payload(event["result"])
                final_result = public_result
                final_answer = public_result.get("answer", "")
                used_retrieval = bool(public_result.get("used_retrieval", False))
                collected_evidence = public_result.get("evidence", [])
                yield {**event, "result": public_result}

                # --- Log session ---
                latency_ms = int((time.monotonic() - start_time) * 1000)
                model_cfg = final_result.get("debug", {}).get("model_config") or {
                    "encoder": _ACTIVE_CONFIG.get("encoder", "hashing"),
                    "generator": _ACTIVE_CONFIG.get("generator", "template"),
                    "top_k": _ACTIVE_CONFIG.get("top_k", 4),
                    "min_similarity": _ACTIVE_CONFIG.get("min_similarity", 0.02),
                }
                entry = SessionLogger.build_entry(
                    session_id=session_id,
                    question_raw=question_raw,
                    question_pipeline=question_pipeline,
                    model_config=model_cfg,
                    attached_image=attached_image,
                    retrieval={
                        "used": used_retrieval,
                        "hits": collected_hits,
                        "top_hit_score": collected_hits[0].get("score", 0.0) if collected_hits else 0.0,
                    },
                    evidence=[
                        {k: v for k, v in e.items() if k in
                         ("image_id", "diagnosis", "body_part", "rerank_score", "retrieval_score")}
                        for e in collected_evidence
                    ],
                    answer=final_answer,
                    latency_ms=latency_ms,
                )
                # Compute inline eval scores
                eval_scores = EVALUATOR.score_session(entry)
                entry["eval_scores"] = eval_scores
                SESSION_LOGGER.log(entry)
                continue

            yield event

    def _serve_frontend_asset(self, route: str) -> bool:
        if not FRONTEND_DIST.exists():
            return False
        if route == "/":
            self._send_file(FRONTEND_DIST / "index.html")
            return True
        candidate = FRONTEND_DIST / route.removeprefix("/")
        if candidate.exists() and candidate.is_file():
            self._send_file(candidate)
            return True
        if route.startswith("/assets/"):
            self._send_json({"error": "asset not found"}, status=404)
            return True
        return False

    # ------------------------------------------------------------------
    # GET routes
    # ------------------------------------------------------------------

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/records":
            pipeline = _get_pipeline()
            self._send_json([self._record_to_public_payload(r) for r in pipeline.records_as_dicts()])
            return

        if route.startswith("/api/image/"):
            image_id = unquote(route.removeprefix("/api/image/")).strip()
            if not image_id:
                self._send_json({"error": "image id is required"}, status=400)
                return
            self._send_record_image(image_id)
            return

        if route == "/api/answer-stream":
            qs = parse_qs(parsed.query)
            question = qs.get("question", [""])[0].strip()
            session_id = qs.get("session_id", [f"session-{int(time.time()*1000)}"])[0]
            question_raw = qs.get("question_raw", [question])[0].strip()
            attached_image_raw = qs.get("attached_image", [""])[0].strip()
            attached_image: dict | None = None
            if attached_image_raw:
                try:
                    attached_image = json.loads(attached_image_raw)
                except json.JSONDecodeError:
                    pass

            if not question:
                self._send_sse([{"type": "error", "message": "question is required"}])
                return

            pipeline = _get_pipeline()
            self._send_sse(
                self._public_stream_events(
                    pipeline.answer_events(question),
                    session_id=session_id,
                    question_raw=question_raw,
                    question_pipeline=question,
                    attached_image=attached_image,
                )
            )
            return

        if route == "/api/model-configs":
            from main_algo.encoder import AVAILABLE_ENCODERS  # type: ignore[attr-defined]
            self._send_json({
                "active": _ACTIVE_CONFIG,
                "encoders": AVAILABLE_ENCODERS,
                "generators": AVAILABLE_GENERATORS,
            })
            return

        if route == "/api/sessions":
            sessions = SESSION_LOGGER.load_all()
            self._send_json(sessions)
            return

        if self._serve_frontend_asset(route):
            return

        if route == "/":
            self._send_file(WEB_ROOT / "index.html")
            return

        if route.startswith("/static/"):
            self._send_file(WEB_ROOT / route.removeprefix("/static/"))
            return

        self._send_json({"error": "not found"}, status=404)

    # ------------------------------------------------------------------
    # POST routes
    # ------------------------------------------------------------------

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, status=400)
            return

        if route == "/api/set-config":
            global _ACTIVE_CONFIG
            _ACTIVE_CONFIG = {
                "encoder": str(payload.get("encoder", _ACTIVE_CONFIG.get("encoder", "hashing"))),
                "generator": str(payload.get("generator", _ACTIVE_CONFIG.get("generator", "template"))),
                "gemini_api_key": str(payload.get("gemini_api_key", _ACTIVE_CONFIG.get("gemini_api_key", ""))),
                "gemini_model": str(payload.get("gemini_model", _ACTIVE_CONFIG.get("gemini_model", "gemini-1.5-flash"))),
                "top_k": int(payload.get("top_k", _ACTIVE_CONFIG.get("top_k", 4))),
                "min_similarity": float(payload.get("min_similarity", _ACTIVE_CONFIG.get("min_similarity", 0.02))),
            }
            # Eagerly init new pipeline
            try:
                _get_pipeline(_ACTIVE_CONFIG)
                self._send_json({"ok": True, "active": _ACTIVE_CONFIG})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if route == "/api/feedback":
            session_id = str(payload.get("session_id", "")).strip()
            rating = payload.get("rating")
            if not session_id or rating not in (1, -1):
                self._send_json({"error": "session_id and rating (1 or -1) are required"}, status=400)
                return
            updated = SESSION_LOGGER.update_feedback(session_id, int(rating))
            self._send_json({"ok": updated})
            return

        if route == "/api/answer":
            question = str(payload.get("question", "")).strip()
            if not question:
                self._send_json({"error": "question is required"}, status=400)
                return
            pipeline = _get_pipeline()
            result = pipeline.answer(question)
            self._send_json(self._result_to_public_payload(result.to_dict()))
            return

        self._send_json({"error": "not found"}, status=404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BoneRAG demo app server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument(
        "--encoder",
        default="hashing",
        choices=["hashing", "biomedclip", "clip"],
        help="Default encoder on startup",
    )
    parser.add_argument(
        "--generator",
        default="template",
        choices=["template", "gemini"],
        help="Default generator on startup",
    )
    args = parser.parse_args()

    _ACTIVE_CONFIG["encoder"] = args.encoder
    _ACTIVE_CONFIG["generator"] = args.generator
    # Re-init default pipeline with CLI args
    _get_pipeline()

    server = ThreadingHTTPServer((args.host, args.port), BoneRAGHandler)
    print(f"[demo-app] running at http://{args.host}:{args.port}/")
    print(f"[demo-app] encoder={args.encoder}  generator={args.generator}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo-app] stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
