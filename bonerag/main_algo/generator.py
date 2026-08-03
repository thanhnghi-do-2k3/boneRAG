"""Generator layer for BoneRAG pipeline.

Focuses exclusively on Local Small-Parameter Foundation Models (Local SLMs) and pure RAG context synthesis.
Commercial mega-LLMs (Gemini, OpenAI) are excluded to prevent parametric knowledge contamination / data leakage,
ensuring that diagnostic performance strictly benchmarks the Image RAG retrieval quality.
"""

from __future__ import annotations

import json
import urllib.request
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pipeline import Evidence


class BaseGenerator(ABC):
    """Abstract answer generator used by BoneRAGPipeline."""

    @abstractmethod
    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        """Generate a natural-language answer given question + retrieved evidence."""

    @property
    def name(self) -> str:
        return self.__class__.__name__


_SYSTEM_PROMPT = """\
Bạn là BoneRAG, một hệ thống chuyên gia y khoa dựa trên kỹ thuật Image Retrieval-Augmented Generation (Image RAG).
Nhiệm vụ của bạn: Chỉ sử dụng các bằng chứng hình ảnh X-quang được trích xuất từ cơ sở dữ liệu để phân tích câu hỏi lâm sàng.
Không suy đoán ngoài các bằng chứng được cung cấp. Trả lời bằng tiếng Việt chuyên môn y khoa.
"""

def _build_rag_prompt(question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
    if not used_retrieval or not evidence:
        return (
            f"Câu hỏi lâm sàng: {question}\n\n"
            "Không tìm thấy bằng chứng X-quang liên quan trong cơ sở dữ liệu. "
            "Hãy thông báo rằng hệ thống cần thêm thông tin hoặc hình ảnh X-quang cụ thể hơn."
        )

    evidence_text = "\n".join(
        f"[Evidence {i+1}] Ca ID: {e.image_id} | Tiêu đề: {e.title} | Vùng: {e.region} | Bộ phận: {e.body_part} "
        f"| Chẩn đoán: {e.diagnosis} | Dạng tổn thương: {e.fracture_type} | Điểm tương đồng RAG: {e.rerank_score:.3f}\n"
        f"  Ghi chú lâm sàng: {e.evidence_note}"
        for i, e in enumerate(evidence[:4])
    )
    return (
        f"Câu hỏi lâm sàng: {question}\n\n"
        f"Các bằng chứng hình ảnh X-quang tương đồng được trích xuất từ CSDL:\n{evidence_text}\n\n"
        "Hãy tổng hợp phân tích lâm sàng và đưa ra chẩn đoán dựa CHÍNH XÁC trên các bằng chứng trên."
    )


# ---------------------------------------------------------------------------
# 1. LocalRAGSynthesizer — Pure Evidence Synthesizer (0% Prior Knowledge Leakage)
# ---------------------------------------------------------------------------

class LocalRAGSynthesizer(BaseGenerator):
    """Pure evidence-based local synthesizer.
    
    Generates natural clinical assessment strictly from RAG evidence without prior data leakage.
    """

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        if not used_retrieval or not evidence:
            return (
                "⚠️ **BoneRAG Local RAG Evaluation:**\n\n"
                "Không tìm thấy bằng chứng hình ảnh X-quang có điểm tương đồng đạt ngưỡng trong CSDL.\n"
                "👉 *Đánh giá Benchmark:* Cần cung cấp hình ảnh X-quang rõ nét hoặc câu hỏi y khoa cụ thể hơn."
            )

        top = evidence[0]
        ref_cases = evidence[:3]

        lines = [
            "🏥 **Báo cáo Chẩn đoán Hình ảnh (BoneRAG Local SLM Benchmark)**",
            "---",
            f"❓ **Câu hỏi lâm sàng:** *\"{question}\"*",
            "",
            "🔍 **1. Bằng chứng Hình ảnh RAG Truy xuất (BiomedCLIP Vector Matching):**",
            f"- **Ca tương đồng nhất (Top-1):** ID `{top.image_id}` ({top.title})",
            f"- **Vùng giải phẫu & Bộ phận:** {top.region} ({top.body_part})",
            f"- **Điểm tương đồng RAG (Rerank Score):** `{top.rerank_score:.3f}`",
            f"- **Ghi chú bằng chứng y khoa:** {top.evidence_note}",
            "",
            "🩺 **2. Nhận định Tổn thương & Kết luận Chẩn đoán:**",
            f"- **Chẩn đoán RAG:** Nghi ngờ **{top.diagnosis}** tại {top.region}.",
            f"- **Đặc điểm đường gãy/tổn thương:** {top.fracture_type if top.fracture_type else 'Cần đối chiếu các thế chụp thẳng/nghiêng'}.",
        ]

        if len(ref_cases) > 1:
            lines.append("")
            lines.append("📋 **3. Đối chiếu Các ca Tương đồng trong CSDL:**")
            for idx, item in enumerate(ref_cases, 1):
                lines.append(
                    f"  {idx}. **{item.title}** (`{item.image_id}`): Vùng {item.region} | "
                    f"Chẩn đoán: *{item.diagnosis}* | Điểm RAG: `{item.rerank_score:.3f}`"
                )

        lines.extend([
            "",
            "💡 **4. Khuyến nghị Lâm sàng:**",
            "- Thăm khám điểm đau chói, kiểm tra mạch ngoại vi và vận động ngọn chi.",
            "- Cố định tạm thời và chỉ định chụp CT Scanner nếu nghi ngờ gãy kín/phức tạp.",
            "",
            "---",
            "⚠️ *Lưu ý đánh giá: Kết quả được tổng hợp trực tiếp từ RAG context nhằm đảm bảo tính khách quan cho Benchmark, không dùng tri thức ẩn của LLM thương mại.*"
        ])

        return "\n".join(lines)


# Backward-compatibility alias
TemplateGenerator = LocalRAGSynthesizer


# ---------------------------------------------------------------------------
# 2. LocalHuggingFaceGenerator — Local Small Language Models (< 2B Params)
# ---------------------------------------------------------------------------

class LocalHuggingFaceGenerator(BaseGenerator):
    """Local Small-Parameter Language Model (SLM) using HuggingFace transformers.
    
    Using small open models (Qwen2.5-0.5B, Qwen2.5-1.5B, SmolLM2-1.7B) prevents
    prior knowledge contamination, ensuring that output accuracy strictly reflects RAG quality.
    """

    def __init__(self, model_name: str = "Qwen/Qwen2.5-0.5B-Instruct") -> None:
        self.model_name = model_name
        self._tokenizer: Any = None
        self._model: Any = None

    def _get_model_and_tokenizer(self) -> tuple[Any, Any]:
        if self._model is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if device != "cpu" else torch.float32,
            )
            self._model.to(device)
        return self._tokenizer, self._model

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        prompt = _build_rag_prompt(question, evidence, used_retrieval)
        try:
            tokenizer, model = self._get_model_and_tokenizer()
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
            generated_ids = model.generate(**model_inputs, max_new_tokens=400, temperature=0.3)
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return response.strip()
        except Exception as exc:
            return (
                f"⚠️ **[Local SLM Note]** Không thể nạp weights `{self.model_name}` ({exc}).\n\n"
                + LocalRAGSynthesizer().generate(question, evidence, used_retrieval)
            )

    @property
    def name(self) -> str:
        return f"LocalSLM({self.model_name})"


# ---------------------------------------------------------------------------
# 3. OllamaLocalGenerator — Local Ollama / vLLM Endpoint
# ---------------------------------------------------------------------------

class OllamaLocalGenerator(BaseGenerator):
    """Local Ollama / vLLM endpoint runner on localhost:11434."""

    def __init__(self, model: str = "qwen2.5:0.5b", host: str = "http://localhost:11434") -> None:
        self.model = model
        self.host = host.rstrip("/")

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        prompt = _build_rag_prompt(question, evidence, used_retrieval)
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "system": _SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data.get("response", "").strip()
        except Exception as exc:
            return (
                f"⚠️ **[Ollama Local Error]** Không kết nối được server Ollama tại {self.host} ({exc}).\n\n"
                + LocalRAGSynthesizer().generate(question, evidence, used_retrieval)
            )


# ---------------------------------------------------------------------------
# Factory & Registries
# ---------------------------------------------------------------------------

def get_generator(name: str = "local_context_synth", **kwargs: Any) -> BaseGenerator:
    """Return generator instance by name.

    Args:
        name: "local_context_synth" | "qwen_05b" | "qwen_15b" | "smollm_17b" | "ollama_local"
    """
    if name == "qwen_05b":
        return LocalHuggingFaceGenerator("Qwen/Qwen2.5-0.5B-Instruct")
    if name == "qwen_15b":
        return LocalHuggingFaceGenerator("Qwen/Qwen2.5-1.5B-Instruct")
    if name == "smollm_17b":
        return LocalHuggingFaceGenerator("HuggingFaceTB/SmolLM2-1.7B-Instruct")
    if name == "ollama_local":
        model = kwargs.get("model", "qwen2.5:0.5b")
        host = kwargs.get("host", "http://localhost:11434")
        return OllamaLocalGenerator(model=model, host=host)

    # Default: LocalRAGSynthesizer (Pure evidence synthesis, zero data leakage)
    return LocalRAGSynthesizer()


AVAILABLE_GENERATORS = {
    "local_context_synth": {
        "label": "BoneRAG Evidence Synthesizer (0% Prior Leakage)",
        "description": "Mô hình tổng hợp RAG context thuần túy. Đảm bảo 0% rò rỉ tri thức ẩn, phục vụ Benchmark khách quan.",
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

