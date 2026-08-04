"""Evidence Citation Synthesizer for BoneRAG.

Formats medical evidence citations into generated responses,
linking clinical findings back to source image IDs and bounding boxes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bonerag.main_algo.pipeline import Evidence


class EvidenceCitationSynthesizer:
    """Formatter to attach structured evidence citations to medical VQA answers."""

    def format_citations(self, evidence_list: list[Evidence]) -> str:
        """Format retrieved evidence items into structured Markdown citation footnotes."""
        if not evidence_list:
            return ""

        citation_lines = ["\n\n---", "### 📌 Trích dẫn Nguồn Bằng chứng X-quang (Evidence Citations):"]
        for idx, ev in enumerate(evidence_list, start=1):
            bbox_str = f", Tọa độ BBox ROI: {len(ev.fracture_boxes)} vùng" if ev.fracture_boxes else ""
            line = (
                f"{idx}. **[Doc: `{ev.image_id}`]** - {ev.title} "
                f"*(Vị trí: {ev.body_part} | Chẩn đoán: {ev.diagnosis}{bbox_str})*"
            )
            citation_lines.append(line)

        return "\n".join(citation_lines)

    def attach_inline_citations(self, text: str, evidence_list: list[Evidence]) -> str:
        """Attach inline citation tags [Doc: image_id] to natural language text."""
        if not evidence_list:
            return text

        primary_doc = evidence_list[0].image_id
        citation_footer = self.format_citations(evidence_list)
        return f"{text} [Doc: `{primary_doc}`]{citation_footer}"
