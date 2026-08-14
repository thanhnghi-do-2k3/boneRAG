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
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

if __package__ in {None, ""}:
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    sys.path.append(str(Path(__file__).resolve().parents[1] / "bonerag"))

from main_algo.encoder import get_multimodal_encoder, AVAILABLE_ENCODERS
from main_algo.generator import get_generator, AVAILABLE_GENERATORS
from main_algo.pipeline import BoneRAGPipeline
from evaluation.session_logger import SessionLogger
from evaluation.evaluator import BoneRAGEvaluator

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
FRONTEND_DIST = ROOT / "frontend" / "dist"

AVAILABLE_ENCODERS = {
    "biomedclip": {
        "label": "BiomedCLIP (Microsoft)",
        "description": "Biomedical CLIP (PubMedBERT + ViT-B/16). Purpose-built for medical VQA & X-ray RAG.",
        "requires_download": True,
        "download_size_mb": 400,
    },
    "clip_vit_b32": {
        "label": "CLIP ViT-B/32 (OpenAI)",
        "description": "OpenAI general-purpose vision-language CLIP model.",
        "requires_download": True,
        "download_size_mb": 350,
    },
    "clip_vit_l14": {
        "label": "CLIP ViT-L/14 (OpenAI)",
        "description": "OpenAI high-resolution Vision-Language model (768-dim embeddings).",
        "requires_download": True,
        "download_size_mb": 850,
    },
    "resnet_text": {
        "label": "ResNet50 + Medical Embedder",
        "description": "ResNet50 visual backbone with text vectorizer baseline.",
        "requires_download": True,
        "download_size_mb": 200,
    },
}

AVAILABLE_GENERATORS = {
    "local_context_synth": {
        "label": "BoneRAG Evidence Synthesizer (0% Prior Leakage)",
        "description": "Mô hình tổng hợp RAG context thuần túy. Đảm bảo 0% rò rỉ tri thức ẩn, phục vụ Benchmark RAG khách quan.",
        "requires_key": False,
    },
    "qwen_05b": {
        "label": "Qwen2.5-0.5B Local SLM (0.5B Params)",
        "description": "Mô hình Foundation Model nhỏ gọn chạy cục bộ (0.5B parameters). Tự động nạp weights nhẹ.",
        "requires_key": False,
    },
    "qwen_15b": {
        "label": "Qwen2.5-1.5B Local SLM (1.5B Params)",
        "description": "Mô hình Foundation Model cân bằng chạy cục bộ (1.5B parameters).",
        "requires_key": False,
    },
    "smollm_17b": {
        "label": "SmolLM2-1.7B Local SLM (1.7B Params)",
        "description": "Mô hình Foundation Model open-weights chạy cục bộ (1.7B parameters).",
        "requires_key": False,
    },
    "ollama_local": {
        "label": "Ollama Local Endpoint (Qwen / Llama / Phi)",
        "description": "Kết nối tới server Ollama/vLLM chạy cục bộ tại http://localhost:11434.",
        "requires_key": False,
        "models": ["qwen2.5:0.5b", "qwen2.5:1.5b", "llama3.2:1b", "smollm2:1.7b"],
        "default_model": "qwen2.5:0.5b",
    },
}

# ---------------------------------------------------------------------------
# Global state — pipeline cache + session logger
# ---------------------------------------------------------------------------

_PIPELINE_CACHE: dict[str, BoneRAGPipeline] = {}
_ACTIVE_CONFIG: dict = {
    "encoder": "biomedclip",
    "generator": "local_context_synth",
    "top_k": 4,
    "min_similarity": 0.02,
}

SESSION_LOGGER = SessionLogger()
EVALUATOR = BoneRAGEvaluator()


_PIPELINE_LOCK = threading.Lock()

# Tracks loading state per cache key: 'loading' | 'ready' | 'error:<msg>'
_MODEL_LOADING_STATUS: dict[str, str] = {}
_MODEL_LOADING_EVENTS: dict[str, threading.Event] = {}


def _pipeline_cache_key(config: dict) -> str:
    return f"{config['encoder']}|{config['generator']}|{config.get('gemini_model', '')}|{config.get('openai_api_key', '')}|{config['top_k']}|{config['min_similarity']}"


def _normalize_generator_name(gen_name: str) -> str:
    if gen_name not in AVAILABLE_GENERATORS:
        return "local_context_synth"
    return gen_name


def _get_pipeline(config: dict | None = None) -> BoneRAGPipeline:
    """Return a cached pipeline for the given config, or for ACTIVE_CONFIG."""
    cfg = config or _ACTIVE_CONFIG
    encoder_name = cfg.get("encoder", "biomedclip")
    gen_name = _normalize_generator_name(cfg.get("generator", "local_context_synth"))
    key = f"{encoder_name}|{gen_name}|{cfg.get('top_k', 4)}|{cfg.get('min_similarity', 0.02)}|strict={bool(cfg.get('strict_encoder', False))}"
    with _PIPELINE_LOCK:
        if key not in _PIPELINE_CACHE:
            _MODEL_LOADING_STATUS[key] = "loading"
            _MODEL_LOADING_EVENTS[key] = threading.Event()
            try:
                encoder = get_multimodal_encoder(
                    mode=encoder_name,
                    strict=bool(cfg.get("strict_encoder", False)),
                )
                generator = get_generator(
                    gen_name,
                    strict=bool(cfg.get("strict_generator", False)),
                )

                # Locate pre-computed FAISS index & metadata for full FracAtlas dataset (4,082 X-rays)
                repo_root = Path(__file__).resolve().parents[1]
                idx_name = "biomedclip" if "biomed" in encoder_name else ("clip_vitl14" if "l14" in encoder_name else "clip_vitb32")
                artifact_dir = repo_root / "bonerag" / "artifacts" / "fracatlas"
                faiss_file = artifact_dir / f"fracatlas_{idx_name}.faiss"
                meta_file = artifact_dir / f"fracatlas_{idx_name}_metadata.json"

                index_path = faiss_file if faiss_file.exists() else None
                metadata_path = meta_file if meta_file.exists() else None

                _PIPELINE_CACHE[key] = BoneRAGPipeline(
                    encoder=encoder,
                    generator=generator,
                    top_k=int(cfg.get("top_k", 4)),
                    min_similarity=float(cfg.get("min_similarity", 0.02)),
                    index_path=index_path,
                    metadata_path=metadata_path,
                )
                _MODEL_LOADING_STATUS[key] = "ready"
            except Exception as exc:
                _MODEL_LOADING_STATUS[key] = f"error:{exc}"
                raise
            finally:
                _MODEL_LOADING_EVENTS[key].set()
        return _PIPELINE_CACHE[key]


def _preload_default_pipeline() -> None:
    """Preload BiomedCLIP + local_context_synth at startup (background)."""
    print("[demo-app] ⏳ Preloading BiomedCLIP encoder + local_context_synth generator...")
    try:
        _get_pipeline(_ACTIVE_CONFIG)
        print("[demo-app] ✅ Default pipeline ready!")
    except Exception as exc:
        print(f"[demo-app] ❌ Preload failed: {exc}")


def _rule_based_benchmark_analysis(summary: dict) -> str:
    systems = summary.get("systems") if isinstance(summary, dict) else []
    if not isinstance(systems, list) or not systems:
        return "Chưa có đủ dữ liệu benchmark để nhận xét."

    def metric(system: dict, key: str) -> float:
        try:
            return float(system.get(key, 0.0))
        except (TypeError, ValueError):
            return 0.0

    best_decision = max(systems, key=lambda item: metric(item, "decision_label_accuracy"))
    best_retrieval = max(systems, key=lambda item: metric(item, "retrieval_top1_label_accuracy"))
    best_answer = max(systems, key=lambda item: metric(item, "answer_label_accuracy"))
    ours = next((item for item in systems if item.get("system_key") == "bonerag"), None)
    calibrated = next((item for item in systems if item.get("system_key") == "bonerag_answer_calibrated"), None)
    image_only = next((item for item in systems if item.get("system_key") == "image_rag"), None)

    lines = [
        "Nhận xét tự động:",
        f"- Decision tốt nhất hiện là {best_decision.get('system_label')} với accuracy {metric(best_decision, 'decision_label_accuracy'):.1%}.",
        f"- Retrieval tốt nhất hiện là {best_retrieval.get('system_label')} với Top-1 {metric(best_retrieval, 'retrieval_top1_label_accuracy'):.1%}.",
        f"- Answer label tốt nhất hiện là {best_answer.get('system_label')} với accuracy {metric(best_answer, 'answer_label_accuracy'):.1%}.",
    ]
    if ours and image_only:
        delta_decision = metric(ours, "decision_label_accuracy") - metric(image_only, "decision_label_accuracy")
        delta_top1 = metric(ours, "retrieval_top1_label_accuracy") - metric(image_only, "retrieval_top1_label_accuracy")
        delta_p4 = metric(ours, "evidence_label_precision_at_4") - metric(image_only, "evidence_label_precision_at_4")
        delta_answer = metric(ours, "answer_label_accuracy") - metric(image_only, "answer_label_accuracy")
        lines.append(
            f"- So với Image-only RAG, BoneRAG chênh Decision {delta_decision:+.1%}, Top-1 {delta_top1:+.1%}, P@4 {delta_p4:+.1%}, Answer {delta_answer:+.1%}."
        )
        if delta_top1 <= 0 and delta_p4 <= 0:
            lines.append("- Chưa nên claim BoneRAG là retrieval method tốt hơn; cần cải thiện reranker/evidence selection trước.")
        elif delta_top1 > 0 or delta_p4 > 0:
            lines.append("- Có tín hiệu cải thiện retrieval, nhưng vẫn nên báo confidence interval và phân tích per-case.")
    if ours and calibrated:
        delta_cal_answer = metric(calibrated, "answer_label_accuracy") - metric(ours, "answer_label_accuracy")
        lines.append(
            f"- Answer calibration chênh BoneRAG gốc {delta_cal_answer:+.1%}; nếu tăng thì chỉ được claim cải thiện answer-level, không phải retrieval-level."
        )
    lines.append("- Bảng này là internal ablation. Paper-method proxy đã bị loại; không so trực tiếp với MMed-RAG/RULE/FactMM-RAG nếu chưa chạy official method trên cùng protocol.")
    return "\n".join(lines)


def _gemini_benchmark_analysis(summary: dict, cases: list | None = None) -> tuple[str, str]:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return _rule_based_benchmark_analysis(summary), "rule_based"

    import urllib.request
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent?key="
        + quote(api_key, safe="")
    )
    compact_cases = []
    if isinstance(cases, list):
        for item in cases[:160]:
            if isinstance(item, dict):
                compact_cases.append({
                    "case_id": item.get("case_id"),
                    "system_key": item.get("system_key"),
                    "expected": item.get("expected_diagnosis"),
                    "decision": item.get("decision_predicted_diagnosis"),
                    "decision_correct": item.get("decision_label_accuracy"),
                    "decision_source": item.get("decision_source"),
                    "top": item.get("predicted_top_diagnosis"),
                    "evidence_majority": item.get("evidence_majority_diagnosis"),
                    "answer": item.get("answer_predicted_diagnosis"),
                    "retrieval_correct": item.get("retrieval_top1_label_accuracy"),
                    "answer_correct": item.get("answer_label_accuracy"),
                    "answer_matches_evidence_majority": item.get("answer_matches_evidence_majority"),
                    "answer_factuality_score": item.get("answer_factuality_score"),
                })
    prompt = (
        "Bạn là reviewer nghiên cứu Medical Image RAG. Hãy nhận xét benchmark này bằng tiếng Việt, "
        "ngắn gọn nhưng sắc bén. Đây là internal ablation, không phải so sánh trực tiếp với paper khác. "
        "Không được claim vượt MMed-RAG/RULE/FactMM-RAG nếu chưa reproduction chính thức. "
        "Benchmark này là FracAtlas-derived closed grounded VQA pilot: câu hỏi sinh từ annotation, "
        "không phải native clinician-authored VQA và chưa score query-image localization. "
        "Nêu: hệ tốt nhất theo final decision, hệ tốt nhất theo retrieval, hệ tốt nhất theo answer, BoneRAG có đủ mạnh chưa, "
        "factuality/grounding metric có đáng tin đến đâu, lỗi metric/thiên lệch cần kiểm tra, "
        "và 3 bước cải thiện tiếp theo gồm BTXRD/GRAZ/RadBench hoặc ImageCLEF nếu phù hợp.\n\n"
        f"SUMMARY JSON:\n{json.dumps(summary, ensure_ascii=False)[:12000]}\n\n"
        f"CASE AUDIT SAMPLE:\n{json.dumps(compact_cases, ensure_ascii=False)[:12000]}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 900},
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        return text or _rule_based_benchmark_analysis(summary), "gemini"
    except Exception as exc:
        return _rule_based_benchmark_analysis(summary) + f"\n\nGemini fallback: {exc}", "rule_based_fallback"



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
        try:
            raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "not found"}, status=404)
            return
        try:
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_sse(self, events) -> None:
        import threading
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Thread-safe write lock to prevent keepalive + main thread from
            # interleaving writes to self.wfile and corrupting SSE frames.
            write_lock = threading.Lock()

            # Keepalive thread: sends SSE comment ping every 10s to prevent connection drop
            stop_event = threading.Event()
            def _keepalive():
                while not stop_event.is_set():
                    try:
                        with write_lock:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                    except Exception:
                        break
                    stop_event.wait(10)
            ka_thread = threading.Thread(target=_keepalive, daemon=True)
            ka_thread.start()

            try:
                for event in events:
                    raw = f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n".encode("utf-8")
                    with write_lock:
                        self.wfile.write(raw)
                        self.wfile.flush()
                    time.sleep(0.02)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                # Send error event to frontend so it can show the error
                # instead of spinning forever with "Đang suy nghĩ..."
                print(f"[demo-app] ❌ SSE generator error: {exc}")
                import traceback
                traceback.print_exc()
                try:
                    err_event = {"type": "error", "message": f"Server error: {exc}"}
                    raw = f"data: {json.dumps(err_event, ensure_ascii=False, default=str)}\n\n".encode("utf-8")
                    with write_lock:
                        self.wfile.write(raw)
                        self.wfile.flush()
                except Exception:
                    pass
            finally:
                stop_event.set()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")
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

    def _generate_medical_xray_svg(self, record) -> bytes:
        body_part = str(getattr(record, "body_part", "X-ray")).upper()
        diagnosis = str(getattr(record, "diagnosis", "Case")).upper()
        title = str(getattr(record, "title", "Medical Case"))
        image_id = str(getattr(record, "image_id", "sample"))

        is_fracture = "frac" in diagnosis.lower() or "frac" in image_id.lower() or "gãy" in diagnosis.lower()
        badge_color = "#ef4444" if is_fracture else "#10b981"

        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 600" width="500" height="600">
  <defs>
    <radialGradient id="xrayGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.25"/>
      <stop offset="60%" stop-color="#0f172a" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#020617" stop-opacity="1"/>
    </radialGradient>
    <pattern id="grid" width="25" height="25" patternUnits="userSpaceOnUse">
      <path d="M 25 0 L 0 0 0 25" fill="none" stroke="#1e293b" stroke-width="0.5"/>
    </pattern>
  </defs>

  <rect width="100%" height="100%" fill="#020617"/>
  <rect width="100%" height="100%" fill="url(#grid)"/>
  <circle cx="250" cy="300" r="230" fill="url(#xrayGlow)"/>

  <!-- Bone Anatomy Illustration -->
  <g stroke="#e2e8f0" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.85">
    <path d="M 230 100 L 230 500 M 270 100 L 270 500" stroke-width="12" stroke="#cbd5e1"/>
    <path d="M 200 90 C 210 60, 290 60, 300 90 C 290 120, 210 120, 200 90 Z" fill="#94a3b8"/>
    <path d="M 200 510 C 210 480, 290 480, 300 510 C 290 540, 210 540, 200 510 Z" fill="#94a3b8"/>
    {"<path d='M 215 310 L 285 290' stroke='#ef4444' stroke-width='7' stroke-dasharray='5 2'/>" if is_fracture else ""}
  </g>

  <!-- Medical Annotations -->
  <rect x="25" y="25" width="130" height="32" rx="6" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5"/>
  <text x="90" y="46" fill="#38bdf8" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">R - {body_part}</text>

  <rect x="335" y="25" width="140" height="32" rx="6" fill="#0f172a" stroke="{badge_color}" stroke-width="1.5"/>
  <text x="405" y="46" fill="{badge_color}" font-family="sans-serif" font-size="13" font-weight="bold" text-anchor="middle">{diagnosis}</text>

  <!-- Title & ID overlay -->
  <rect x="20" y="520" width="460" height="60" rx="8" fill="#0f172a" stroke="#334155" stroke-width="1"/>
  <text x="35" y="546" fill="#f8fafc" font-family="sans-serif" font-size="15" font-weight="bold">{title}</text>
  <text x="35" y="566" fill="#64748b" font-family="sans-serif" font-size="12">ID: {image_id}</text>
</svg>'''
        return svg_content.encode("utf-8")

    def _send_record_image(self, image_id: str) -> None:
        pipeline = _get_pipeline()
        record = pipeline.record_by_id.get(image_id)
        if record and record.image_path:
            raw_path = Path(record.image_path)
            candidates = [
                raw_path.expanduser().resolve(),
                (WEB_ROOT.parent / raw_path).resolve(),
                Path("/content") / raw_path,
                Path("/content/fracatlas_repo") / raw_path.name,
            ]
            # Try subfolder matching (e.g. Fractured/IMG0001729.jpg or Non_fractured/IMG0001729.jpg)
            if raw_path.parent.name:
                candidates.extend([
                    Path("/content/fracatlas_repo") / raw_path.parent.name / raw_path.name,
                    Path("/content/fracatlas_repo/images") / raw_path.parent.name / raw_path.name,
                    Path("/content/fracatlas_repo/FracAtlas/images") / raw_path.parent.name / raw_path.name,
                ])
            # Try _discover_dataset_images_root()
            try:
                from bonerag.main_algo.data import _discover_dataset_images_root, resolve_dataset_image_path
                root = _discover_dataset_images_root()
                if root:
                    candidates.extend([
                        root / raw_path.name,
                        root / raw_path.parent.name / raw_path.name,
                        root.parent / raw_path.name,
                    ])
                resolved = resolve_dataset_image_path(str(raw_path))
                if resolved:
                    candidates.append(resolved)
            except Exception:
                pass

            for cand in candidates:
                if cand.exists() and cand.is_file():
                    self._send_file(cand)
                    return

        # Fallback for sample/baseline records without local file path
        svg_bytes = self._generate_medical_xray_svg(record or type("Record", (), {"image_id": image_id})())
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(svg_bytes)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(svg_bytes)

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

            evt_type = event.get("type")
            if evt_type == "stage":
                if "hits" in event:
                    collected_hits = event.get("hits", [])
                yield event
            elif evt_type == "token":
                yield event
            elif evt_type == "done" and isinstance(event.get("result"), dict):
                public_result = self._result_to_public_payload(event["result"])
                final_result = public_result
                final_answer = public_result.get("answer", "")
                used_retrieval = bool(public_result.get("used_retrieval", False))
                collected_evidence = public_result.get("evidence", [])
                yield {**event, "result": public_result}

                # --- Log session ---
                latency_ms = int((time.monotonic() - start_time) * 1000)
                model_cfg = final_result.get("debug", {}).get("model_config") or {
                    "encoder": _ACTIVE_CONFIG.get("encoder", "biomedclip"),
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

    def _live_benchmark_stream_events(
        self,
        encoder_name: str,
        generator_name: str,
        total_cases: int = 32,
        include_controls: bool = False,
        include_literature_proxies: bool = False,
    ) -> Iterator[dict[str, object]]:
        """Run the reproducible real-image matrix and stream every case over SSE."""
        from evaluation.benchmark import (
            benchmark_systems,
            build_cases,
            benchmark_runs_path,
            protocol_metadata,
            run_system_case,
            aggregate_case_scores,
        )
        from evaluation.paper_report import build_paper_evaluation

        config = {
            "encoder": encoder_name,
            "generator": generator_name,
            "top_k": 4,
            "min_similarity": 0.02,
            "strict_encoder": True,
            "strict_generator": True,
        }
        try:
            pipe = _get_pipeline(config)
            safe_total_cases = max(2, min(512, int(total_cases)))
            cases = build_cases(pipe.records, cases_per_label=max(1, safe_total_cases // 2))
            systems = benchmark_systems(
                include_controls=include_controls,
                include_literature_proxies=include_literature_proxies,
            )
            protocol = protocol_metadata(cases, systems=systems)
        except Exception as exc:
            yield {
                "type": "bench-error",
                "message": f"Không thể chuẩn bị benchmark dataset thật: {exc}",
            }
            return

        total_runs = len(cases) * len(systems)
        test_query_ids = {case.query_image_id for case in cases}
        yield {
            "type": "bench-start",
            "total": total_runs,
            "total_cases": len(cases),
            "systems": [system["label"] for system in systems],
            "protocol": protocol,
            "encoder": encoder_name,
            "generator": generator_name,
            "message": (
                f"Bắt đầu {protocol['benchmark_version']}: {len(cases)} ảnh thật, "
                f"{len(systems)} hệ thống, toàn bộ test hold-out đã loại khỏi corpus."
            ),
        }

        all_results: list[dict[str, object]] = []
        completed = 0
        for system in systems:
            for case_index, case in enumerate(cases, start=1):
                try:
                    result = run_system_case(pipe, case, system, test_query_ids=test_query_ids)
                    result.update({
                        "case_index": case_index,
                        "total_cases": len(cases),
                        "question": case.question,
                        "system_description": system["description"],
                    })
                    all_results.append(result)
                    completed += 1
                    yield {
                        "type": "bench-case",
                        "index": completed,
                        "total": total_runs,
                        **result,
                    }
                except Exception as exc:
                    yield {
                        "type": "bench-error",
                        "index": completed,
                        "total": total_runs,
                        "case_id": case.case_id,
                        "system_key": system["key"],
                        "system_label": system["label"],
                        "message": f"Benchmark dừng để không ghi partial result: {exc}",
                    }
                    return

        system_summaries = []
        for system in systems:
            scores = [item for item in all_results if item.get("system_key") == system["key"]]
            system_summaries.append({
                "system_key": system["key"],
                "system_label": system["label"],
                "description": system["description"],
                "paper_reference": system.get("paper_reference"),
                **aggregate_case_scores(scores),
            })

        run_record = {
            "run_id": f"benchmark-{int(time.time() * 1000)}",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "protocol": protocol,
            "encoder": encoder_name,
            "generator": generator_name,
            "systems": system_summaries,
            "cases": all_results,
        }
        run_record["paper_evaluation"] = build_paper_evaluation(run_record)
        run_path = benchmark_runs_path()
        write_error = None
        try:
            with run_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(run_record, ensure_ascii=False) + "\n")
        except OSError as exc:
            write_error = str(exc)
            print(f"[benchmark] log write failed: {exc}")

        yield {
            "type": "bench-complete",
            "run_id": run_record["run_id"],
            "summary": {
                **protocol,
                "run_id": run_record["run_id"],
                "created_at": run_record["created_at"],
                "encoder": encoder_name,
                "generator": generator_name,
                "systems": system_summaries,
                "paper_evaluation": run_record["paper_evaluation"],
                "total_evaluated": len(all_results),
                "saved_to": str(run_path) if write_error is None else None,
                "save_error": write_error,
            },
            "message": (
                f"Hoàn tất benchmark thật và đã ghi {run_path}."
                if write_error is None
                else f"Hoàn tất benchmark thật nhưng chưa lưu được file: {write_error}"
            ),
        }

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

        if route == "/api/health":
            self._send_json({
                "ok": True,
                "service": "bonerag-backend",
                "sse": True,
                "active_config": _ACTIVE_CONFIG,
            })
            return

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
            image_data_url: str | None = None
            image_input: str | None = None

            pipeline = _get_pipeline()
            if attached_image_raw:
                try:
                    attached_image = json.loads(attached_image_raw)
                    if isinstance(attached_image, dict):
                        data_url = attached_image.get("data_url")
                        image_id = attached_image.get("image_id")
                        if data_url:
                            image_data_url = str(data_url)
                        elif image_id and image_id in pipeline.record_by_id:
                            rec = pipeline.record_by_id[image_id]
                            if rec.image_path:
                                image_input = rec.image_path
                except Exception:
                    pass

            if not question:
                self._send_sse([{"type": "error", "message": "question is required"}])
                return

            events = self._public_stream_events(
                pipeline.answer_events(question, image_data_url=image_data_url, image_input=image_input),
                session_id=session_id,
                question_raw=question_raw,
                question_pipeline=question,
                attached_image=attached_image,
            )
            self._send_sse(events)
            return

        if route == "/api/model-configs":
            _ACTIVE_CONFIG["generator"] = _normalize_generator_name(_ACTIVE_CONFIG.get("generator", ""))
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

        if route == "/api/benchmark-runs":
            from evaluation.benchmark import benchmark_runs_path

            run_path = benchmark_runs_path()
            runs: list[dict[str, object]] = []
            if run_path.exists():
                with run_path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        try:
                            if line.strip():
                                runs.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            self._send_json(runs[-20:])
            return

        if route == "/api/run-live-benchmark":
            qs = parse_qs(parsed.query)
            enc_name = qs.get("encoder", [_ACTIVE_CONFIG.get("encoder", "biomedclip")])[0]
            gen_name = _normalize_generator_name(qs.get("generator", [_ACTIVE_CONFIG.get("generator", "local_context_synth")])[0])
            include_controls = qs.get("include_controls", ["0"])[0].lower() in {"1", "true", "yes"}
            include_literature_proxies = qs.get("include_literature_proxies", ["0"])[0].lower() in {"1", "true", "yes"}
            try:
                total_cases = int(qs.get("cases", ["32"])[0])
            except (TypeError, ValueError):
                total_cases = 32
            self._send_sse(
                self._live_benchmark_stream_events(
                    enc_name,
                    gen_name,
                    total_cases=total_cases,
                    include_controls=include_controls,
                    include_literature_proxies=include_literature_proxies,
                )
            )
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
            raw_gen = str(payload.get("generator", _ACTIVE_CONFIG.get("generator", "local_context_synth")))
            new_config = {
                "encoder": str(payload.get("encoder", _ACTIVE_CONFIG.get("encoder", "biomedclip"))),
                "generator": _normalize_generator_name(raw_gen),
                "top_k": int(payload.get("top_k", _ACTIVE_CONFIG.get("top_k", 4))),
                "min_similarity": float(payload.get("min_similarity", _ACTIVE_CONFIG.get("min_similarity", 0.02))),
            }
            # Kick off model loading in background thread, then block until ready (max 300s)
            load_done = threading.Event()
            load_err: list[str] = []
            def _load():
                try:
                    _get_pipeline(new_config)
                except Exception as exc:
                    load_err.append(str(exc))
                finally:
                    load_done.set()
            threading.Thread(target=_load, daemon=True).start()
            loaded = load_done.wait(timeout=300)
            if not loaded:
                self._send_json({"ok": False, "error": "Model load timeout (300s). Thử lại sau."}, status=503)
                return
            if load_err:
                self._send_json({"ok": False, "error": load_err[0]}, status=400)
                return
            _ACTIVE_CONFIG = new_config
            self._send_json({"ok": True, "active": _ACTIVE_CONFIG})
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

        if route == "/api/analyze-benchmark":
            summary = payload.get("summary", payload.get("protocol", {}))
            cases = payload.get("cases", [])
            if not isinstance(summary, dict):
                self._send_json({"error": "summary is required"}, status=400)
                return
            analysis, source = _gemini_benchmark_analysis(summary, cases if isinstance(cases, list) else [])
            self._send_json({"ok": True, "source": source, "analysis": analysis})
            return

        if route == "/api/export-benchmark-artifacts":
            from evaluation.paper_report import build_artifact_bundle, build_paper_evaluation

            summary = payload.get("summary", payload.get("protocol", {}))
            cases = payload.get("cases", [])
            if not isinstance(summary, dict):
                self._send_json({"error": "summary is required"}, status=400)
                return
            run_record = {
                "run_id": payload.get("run_id") or summary.get("run_id"),
                "created_at": payload.get("created_at"),
                "protocol": summary,
                "encoder": payload.get("encoder") or summary.get("encoder"),
                "generator": payload.get("generator") or summary.get("generator"),
                "systems": summary.get("systems", []),
                "cases": cases if isinstance(cases, list) else [],
            }
            run_record["paper_evaluation"] = build_paper_evaluation(run_record)
            self._send_json({"ok": True, "artifacts": build_artifact_bundle(run_record)})
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
        default="biomedclip",
        choices=["biomedclip", "clip"],
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

    server = ThreadingHTTPServer((args.host, args.port), BoneRAGHandler)
    print(f"\n[demo-app] 🚀 Server đã khởi động!")
    print(f"[demo-app] 👉 http://{args.host}:{args.port}/")
    print(f"[demo-app] ⏳ Đang preload model: Encoder={args.encoder} | Generator={args.generator}")
    threading.Thread(target=_preload_default_pipeline, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo-app] stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
