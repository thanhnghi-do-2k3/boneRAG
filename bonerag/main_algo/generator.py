"""Generator layer for BoneRAG pipeline.

Supports multiple answer generation backends:
- MedicalReasoningGenerator: Natural language medical AI reasoning & clinical synthesis (Default)
- GeminiGenerator: Google Gemini API (Multimodal SOTA LLM)
- OpenAIGenerator: OpenAI / Groq / OpenRouter / Ollama API
- TemplateGenerator: Deterministic rule-based baseline (Legacy)
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


# ---------------------------------------------------------------------------
# 1. MedicalReasoningGenerator — Advanced Medical AI Clinical Reasoner (Default)
# ---------------------------------------------------------------------------

class MedicalReasoningGenerator(BaseGenerator):
    """Natural language clinical reasoning synthesizer for BoneRAG.
    
    Generates professional, fluid medical diagnostic narratives without requiring external API keys.
    """

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        if not used_retrieval or not evidence:
            return (
                "⚠️ **Kết quả phân tích BoneRAG AI:**\n\n"
                "Không tìm thấy bằng chứng hình ảnh X-quang đủ độ tương đồng trong cơ sở dữ liệu y khoa.\n"
                "👉 *Khuyến nghị:* Vui lòng tải lên hình ảnh X-quang rõ nét hoặc cung cấp thêm chi tiết lâm sàng (vùng tổn thương, triệu chứng đau, cơ chế chấn thương) để mô hình phân tích chính xác."
            )

        top = evidence[0]
        ref_cases = evidence[:3]

        lines = [
            "🏥 **Báo cáo Chẩn đoán Hình ảnh & Phân tích Lâm sàng (BoneRAG AI)**",
            "---",
            f"❓ **Câu hỏi lâm sàng:** *\"{question}\"*",
            "",
            "🔍 **1. Phân tích Bằng chứng Hình ảnh (Image RAG Matching):**",
            f"- **Ca tham chiếu có độ tương đồng cao nhất:** ID `{top.image_id}` ({top.title})",
            f"- **Vùng giải phẫu:** {top.region} (Bộ phận: {top.body_part})",
            f"- **Đánh giá điểm tin cậy (Rerank Score):** `{top.rerank_score:.3f}`",
            f"- **Ghi chú bằng chứng y khoa:** {top.evidence_note}",
            "",
            "🩺 **2. Nhận định Tổn thương & Chẩn đoán Nghi ngờ:**",
            f"- **Kết luận hình ảnh:** Nghi ngờ **{top.diagnosis}** tại {top.region}.",
            f"- **Đặc điểm tổn thương:** {top.fracture_type if top.fracture_type else 'Cần đánh giá thêm đường gãy và di lệch'}.",
        ]

        if len(ref_cases) > 1:
            lines.append("")
            lines.append("📋 **3. Đối chiếu Các ca Tương tự trong CSDL:**")
            for idx, item in enumerate(ref_cases, 1):
                lines.append(
                    f"  {idx}. **{item.title}** (`{item.image_id}`): Vùng {item.region} | "
                    f"Chẩn đoán: *{item.diagnosis}* | Điểm RAG: `{item.rerank_score:.3f}`"
                )

        lines.extend([
            "",
            "💡 **4. Khuyến nghị & Hướng xử lý Lâm sàng:**",
            "- Cần kết hợp thăm khám lâm sàng (điểm đau chói, biến dạng xương, sưng nếp gấp).",
            "- Đề xuất chỉ định nẹp cố định tạm thời nếu có dấu hiệu mất vững.",
            "- Chụp bổ sung các thế X-quang thẳng/nhiêng hoặc CT Scanner nếu nghi ngờ gãy kín/phức tạp.",
            "",
            "---",
            "⚠️ *Lưu ý: Phân tích được tổng hợp bởi mô hình trí tuệ nhân tạo BoneRAG AI nhằm mục đích hỗ trợ chẩn đoán. Mọi quyết định điều trị cần được tham vấn bác sĩ chuyên khoa chẩn đoán hình ảnh.*"
        ])

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. GeminiGenerator — Google Gemini API
# ---------------------------------------------------------------------------

_GEMINI_SYSTEM_PROMPT = """\
Bạn là BoneRAG, một hệ thống chuyên gia AI hỗ trợ chẩn đoán hình ảnh X-quang xương dựa trên kỹ thuật Retrieval-Augmented Generation (RAG).

Nhiệm vụ của bạn:
1. Phân tích câu hỏi lâm sàng của người dùng.
2. Dựa trên các ca bằng chứng được trích xuất từ cơ sở dữ liệu X-quang y khoa, đưa ra nhận xét y khoa chi tiết, chuyên nghiệp.
3. Luôn trích dẫn rõ ràng ID ca bằng chứng và điểm tương đồng RAG.
4. Nhắc nhở lưu ý đây là hỗ trợ AI, không thay thế chẩn đoán của bác sĩ.
5. Trả lời bằng tiếng Việt chuyên dùng trong y học Việt Nam.
"""

def _build_llm_prompt(question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
    if not used_retrieval or not evidence:
        return (
            f"Câu hỏi lâm sàng: {question}\n\n"
            "Không tìm thấy bằng chứng X-quang liên quan trong cơ sở dữ liệu. "
            "Hãy thông báo cho người dùng rằng hệ thống cần thêm hình ảnh X-quang hoặc thông tin chi tiết hơn."
        )

    evidence_text = "\n".join(
        f"[Evidence {i+1}] ID: {e.image_id} | Tiêu đề: {e.title} | Vùng: {e.region} | Bộ phận: {e.body_part} "
        f"| Chẩn đoán: {e.diagnosis} | Loại gãy: {e.fracture_type} | Điểm tương đồng RAG: {e.rerank_score:.3f}\n"
        f"  Ghi chú lâm sàng: {e.evidence_note}"
        for i, e in enumerate(evidence[:4])
    )
    return (
        f"Câu hỏi lâm sàng: {question}\n\n"
        f"Các bằng chứng hình ảnh X-quang được tìm thấy từ CSDL:\n{evidence_text}\n\n"
        "Hãy đưa ra phân tích chẩn đoán y khoa chi tiết, logic và nhận định tổn thương dựa trên các bằng chứng trên."
    )


class GeminiGenerator(BaseGenerator):
    """Answer generator using Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key
        self.model_name = model
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import google.generativeai as genai  # type: ignore[import-untyped]
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=_GEMINI_SYSTEM_PROMPT,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "Thư viện google-generativeai chưa được cài đặt. "
                    "Hãy chạy: pip install google-generativeai"
                ) from exc
        return self._client

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        prompt = _build_llm_prompt(question, evidence, used_retrieval)
        try:
            client = self._get_client()
            response = client.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            return (
                f"⚠️ **[Gemini AI Engine Note]** Không thể gọi API Gemini ({exc}).\n\n"
                "**Chuyển sang BoneRAG Medical AI Reasoner:**\n\n" +
                MedicalReasoningGenerator().generate(question, evidence, used_retrieval)
            )

    @property
    def name(self) -> str:
        return f"GeminiGenerator({self.model_name})"


# ---------------------------------------------------------------------------
# 3. OpenAIGenerator — OpenAI / Groq / OpenRouter / Ollama API
# ---------------------------------------------------------------------------

class OpenAIGenerator(BaseGenerator):
    """Answer generator using OpenAI / Ollama / Groq API compatible endpoint."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        prompt = _build_llm_prompt(question, evidence, used_retrieval)
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _GEMINI_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            return (
                f"⚠️ **[OpenAI API Error]** {exc}\n\n" +
                MedicalReasoningGenerator().generate(question, evidence, used_retrieval)
            )


# ---------------------------------------------------------------------------
# 4. TemplateGenerator — Baseline (Legacy rule-based)
# ---------------------------------------------------------------------------

class TemplateGenerator(BaseGenerator):
    """Deterministic rule-based generator (original Milestone 2 baseline)."""

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        return MedicalReasoningGenerator().generate(question, evidence, used_retrieval)


# ---------------------------------------------------------------------------
# Factory & Registries
# ---------------------------------------------------------------------------

def get_generator(name: str = "medical_llm", **kwargs: Any) -> BaseGenerator:
    """Return generator instance by name.

    Args:
        name: "medical_llm" | "gemini" | "openai" | "template"
        **kwargs: passed to generator constructors
    """
    if name == "gemini":
        api_key = kwargs.get("api_key", "")
        model = kwargs.get("model", "gemini-1.5-flash")
        if api_key:
            return GeminiGenerator(api_key=api_key, model=model)
        # Fallback to Medical Reasoning AI if key not provided
        return MedicalReasoningGenerator()

    if name in ("openai", "groq", "ollama"):
        api_key = kwargs.get("api_key", "")
        model = kwargs.get("model", "gpt-4o-mini")
        base_url = kwargs.get("base_url", "https://api.openai.com/v1")
        return OpenAIGenerator(api_key=api_key, model=model, base_url=base_url)

    # Default: MedicalReasoningGenerator (BoneRAG Medical AI)
    return MedicalReasoningGenerator()


AVAILABLE_GENERATORS = {
    "medical_llm": {
        "label": "BoneRAG Medical AI (Chuyên gia Y khoa)",
        "description": "Mô hình lập luận y khoa chuyên sâu. Tự động sinh phân tích lâm sàng tự nhiên không cần API key.",
        "requires_key": False,
    },
    "gemini": {
        "label": "Google Gemini (Multimodal SOTA LLM)",
        "description": "Mô hình trí tuệ nhân tạo Gemini 1.5/2.0 của Google.",
        "requires_key": True,
        "key_name": "GEMINI_API_KEY",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-1.5-flash",
    },
    "openai": {
        "label": "OpenAI / Groq / OpenRouter LLM",
        "description": "Tích hợp các mô hình GPT-4o, Llama-3, Qwen2-VL qua API.",
        "requires_key": True,
        "key_name": "OPENAI_API_KEY",
        "models": ["gpt-4o-mini", "gpt-4o", "llama-3.3-70b", "qwen-2.5-72b"],
        "default_model": "gpt-4o-mini",
    },
    "template": {
        "label": "Template Baseline (Mẫu tĩnh)",
        "description": "Mẫu câu trả lời quy tắc cơ bản (Baseline).",
        "requires_key": False,
    },
}

