"""HTTP server for the BoneRAG demo app.

Run from the repository root:

    python3 code/demo-app/server.py --port 8088

The server deliberately uses only the Python standard library. The algorithm
implementation lives in ../bonerag; this file only exposes demo API routes
and serves the React build.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

if __package__ in {None, ""}:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1] / "bonerag"))

from main_algo.pipeline import BoneRAGPipeline

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
FRONTEND_DIST = ROOT / "frontend" / "dist"
PIPELINE = BoneRAGPipeline()


class BoneRAGHandler(BaseHTTPRequestHandler):
    server_version = "BoneRAGDemo/0.1"

    def log_message(self, format: str, *args) -> None:
        """Keep server logs compact and explicit."""

        print(f"[demo-app] {self.address_string()} - {format % args}")

    def _send_json(self, payload: dict[str, object] | list[object], status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
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
        self.end_headers()
        for event in events:
            raw = f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(raw)
            self.wfile.flush()
            time.sleep(0.02)

    def _record_to_public_payload(self, record: dict[str, object]) -> dict[str, object]:
        payload = dict(record)
        image_id = str(payload.get("image_id", "")).strip()
        image_path = str(payload.get("image_path", "")).strip()
        if image_id and image_path:
            payload["image_url"] = f"/api/image/{quote(image_id, safe='')}"
        else:
            payload["image_url"] = None
        return payload

    def _result_to_public_payload(self, result: dict[str, object]) -> dict[str, object]:
        payload = dict(result)
        evidence = payload.get("evidence", [])
        if isinstance(evidence, list):
            payload["evidence"] = [
                self._record_to_public_payload(item)
                if isinstance(item, dict)
                else item
                for item in evidence
            ]
        return payload

    def _send_record_image(self, image_id: str) -> None:
        record = PIPELINE.record_by_id.get(image_id)
        if not record or not record.image_path:
            self._send_json({"error": "image not found"}, status=404)
            return

        image_path = Path(record.image_path).expanduser().resolve()
        if not image_path.exists() or not image_path.is_file():
            self._send_json({"error": "image file missing"}, status=404)
            return
        self._send_file(image_path)

    def _public_stream_events(self, events):
        for event in events:
            if isinstance(event, dict) and event.get("type") == "done" and isinstance(event.get("result"), dict):
                yield {**event, "result": self._result_to_public_payload(event["result"])}
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

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/api/records":
            self._send_json([self._record_to_public_payload(record) for record in PIPELINE.records_as_dicts()])
            return
        if route.startswith("/api/image/"):
            image_id = unquote(route.removeprefix("/api/image/")).strip()
            if not image_id:
                self._send_json({"error": "image id is required"}, status=400)
                return
            self._send_record_image(image_id)
            return
        if route == "/api/answer-stream":
            question = parse_qs(parsed.query).get("question", [""])[0].strip()
            if not question:
                self._send_sse([{"type": "error", "message": "question is required"}])
                return
            self._send_sse(self._public_stream_events(PIPELINE.answer_events(question)))
            return
        if self._serve_frontend_asset(route):
            return
        if route == "/":
            self._send_file(WEB_ROOT / "index.html")
            return
        if route.startswith("/static/"):
            relative = route.removeprefix("/static/")
            self._send_file(WEB_ROOT / relative)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route != "/api/answer":
            self._send_json({"error": "not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, status=400)
            return

        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json({"error": "question is required"}, status=400)
            return

        result = PIPELINE.answer(question)
        self._send_json(self._result_to_public_payload(result.to_dict()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BoneRAG demo app server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), BoneRAGHandler)
    print(f"[demo-app] running at http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo-app] stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
