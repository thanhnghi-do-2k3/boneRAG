"""Generator layer for BoneRAG pipeline.

Supports multiple answer generation backends:
- TemplateGenerator: deterministic rule-based (baseline, no LLM needed)
- GeminiGenerator: Google Gemini via generativeai SDK
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
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
# TemplateGenerator — existing baseline logic, no external dependency
# ---------------------------------------------------------------------------

class TemplateGenerator(BaseGenerator):
    """Deterministic rule-based generator (original Milestone 2 baseline)."""

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        if not used_retrieval or not evidence:
            return (
                "Baseline không tìm thấy bằng chứng ảnh đủ liên quan. "
                "Hệ thống nên hỏi thêm ảnh X-quang/câu hỏi cụ thể hơn thay vì đoán."
            )
        top = evidence[0]
        supporting = "; ".join(
            f"{item.title} ({item.body_part}, {item.diagnosis}, score={item.rerank_score:.3f})"
            for item in evidence[:3]
        )
        return (
            f"Câu hỏi: {question}\n\n"
            f"Kết luận Baseline: evidence gần nhất là '{top.title}', vùng {top.region}, "
            f"nhãn {top.diagnosis}. Ghi chú bằng chứng: {top.evidence_note}\n\n"
            f"Các ca được dùng để tham chiếu: {supporting}.\n\n"
            "Lưu ý: đây là baseline kỹ thuật để minh họa Image RAG, không phải chẩn đoán y khoa."
        )


# ---------------------------------------------------------------------------
# GeminiGenerator — Google Gemini API (lazy import, optional dependency)
# ---------------------------------------------------------------------------

_GEMINI_SYSTEM_PROMPT = """\
Bạn là BoneRAG, một hệ thống hỗ trợ chẩn đoán hình ảnh X-quang xương dựa trên Retrieval-Augmented Generation.

Nhiệm vụ của bạn:
1. Phân tích câu hỏi lâm sàng của người dùng.
2. Dựa trên các ca bằng chứng được cung cấp từ cơ sở dữ liệu X-quang, đưa ra nhận xét y khoa phù hợp.
3. Luôn trích dẫn rõ ràng bằng chứng nào bạn dựa vào.
4. Luôn nhắc người dùng rằng đây chỉ là hỗ trợ AI, không thay thế bác sĩ chuyên khoa.
5. Trả lời bằng tiếng Việt trừ khi được yêu cầu khác.

Hãy trả lời súc tích, chính xác, và có cấu trúc rõ ràng."""


def _build_gemini_prompt(question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
    if not used_retrieval or not evidence:
        return (
            f"Câu hỏi: {question}\n\n"
            "Không tìm thấy bằng chứng X-quang liên quan trong cơ sở dữ liệu. "
            "Hãy trả lời rằng hệ thống cần thêm ảnh X-quang cụ thể để phân tích."
        )

    evidence_text = "\n".join(
        f"[Evidence {i+1}] ID: {e.image_id} | Vùng: {e.region} | Bộ phận: {e.body_part} "
        f"| Chẩn đoán: {e.diagnosis} | Loại gãy: {e.fracture_type} "
        f"| Điểm: {e.rerank_score:.3f}\n  Ghi chú: {e.evidence_note}"
        for i, e in enumerate(evidence[:4])
    )
    return (
        f"Câu hỏi lâm sàng: {question}\n\n"
        f"Bằng chứng X-quang từ cơ sở dữ liệu:\n{evidence_text}\n\n"
        "Dựa trên các bằng chứng trên, hãy đưa ra phân tích X-quang phù hợp."
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
                    "google-generativeai is not installed. "
                    "Run: pip install google-generativeai"
                ) from exc
        return self._client

    def generate(self, question: str, evidence: list["Evidence"], used_retrieval: bool) -> str:
        prompt = _build_gemini_prompt(question, evidence, used_retrieval)
        try:
            client = self._get_client()
            response = client.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            return (
                f"[GeminiGenerator Error] {exc}\n\n"
                "Fallback: " + TemplateGenerator().generate(question, evidence, used_retrieval)
            )

    @property
    def name(self) -> str:
        return f"GeminiGenerator({self.model_name})"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_generator(name: str = "template", **kwargs: Any) -> BaseGenerator:
    """Return generator instance by name.

    Args:
        name: "template" | "gemini"
        **kwargs: passed to the generator constructor
            - api_key (str): required for "gemini"
            - model (str): optional Gemini model name
    """
    if name == "gemini":
        api_key = kwargs.get("api_key", "")
        if not api_key:
            raise ValueError("api_key is required for GeminiGenerator")
        model = kwargs.get("model", "gemini-1.5-flash")
        return GeminiGenerator(api_key=api_key, model=model)
    # Default: template
    return TemplateGenerator()


AVAILABLE_GENERATORS = {
    "template": {
        "label": "Template (Baseline)",
        "description": "Rule-based answer generation. No API key needed.",
        "requires_key": False,
    },
    "gemini": {
        "label": "Google Gemini",
        "description": "LLM-powered answer using Google Gemini API.",
        "requires_key": True,
        "key_name": "GEMINI_API_KEY",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-1.5-flash",
    },
}
