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
from urllib.parse import parse_qs, urlparse

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
            time.sleep(0.18)

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
            self._send_json(PIPELINE.records_as_dicts())
            return
        if route == "/api/answer-stream":
            question = parse_qs(parsed.query).get("question", [""])[0].strip()
            if not question:
                self._send_sse([{"type": "error", "message": "question is required"}])
                return
            self._send_sse(PIPELINE.answer_events(question))
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
        self._send_json(result.to_dict())


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
