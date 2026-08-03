"""Multimodal & BiomedCLIP Encoder for BoneRAG Baseline & Production."""

from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import math
from pathlib import Path
import re
from typing import Any

import base64
import io

Vector = tuple[float, ...]
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize(values: list[float] | Any) -> Vector:
    """Return a unit-length vector so dot product behaves like cosine similarity."""

    norm = math.sqrt(sum(float(v) * float(v) for v in values))
    if norm == 0:
        return tuple(float(v) for v in values)
    return tuple(float(v) / norm for v in values)


class BaseMultimodalEncoder(ABC):
    """Abstract base class for BoneRAG encoders."""

    @abstractmethod
    def encode_text(self, text: str) -> Vector:
        pass

    @abstractmethod
    def encode_image(self, image_input: str | Path | Any) -> Vector:
        pass

    @abstractmethod
    def encode_roi(self, image_input: str | Path | Any, bbox: list[float]) -> Vector:
        pass

    def encode_image_from_base64(self, data_url: str) -> Vector:
        """Decode a data URL (data:image/...;base64,...) and encode as image vector.

        This is the key method that enables query-image encoding when a user
        pastes an X-ray image directly into the chat interface.
        """
        # Strip the data URL prefix if present
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        raw = base64.b64decode(data_url)
        # Delegate to encode_image which accepts a PIL Image
        return self._encode_pil_image_bytes(raw)

    def _encode_pil_image_bytes(self, raw_bytes: bytes) -> Vector:
        """Encode raw image bytes. Subclasses that use PIL override this."""
        # Default fallback: treat as text
        return self.encode_text("image visual content xray paste")

    def encode(self, text: str) -> Vector:
        """Backward-compatible alias for encode_text."""
        return self.encode_text(text)


class BiomedCLIPEncoder(BaseMultimodalEncoder):
    """Multimodal encoder utilizing open_clip / BiomedCLIP models."""

    def __init__(
        self,
        model_name: str = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224",
        pretrained: str = "",
    ) -> None:
        import torch
        import open_clip
        from PIL import Image

        self.torch = torch
        self.Image = Image
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_name, pretrained=pretrained
            )
            self.tokenizer = open_clip.get_tokenizer(model_name)
        except Exception:
            # Fallback to standard ViT-B-32 if hub weights require download or network error
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="openai"
            )
            self.tokenizer = open_clip.get_tokenizer("ViT-B-32")

        self.model.to(self.device)
        self.model.eval()

    def encode_text(self, text: str) -> Vector:
        with self.torch.no_grad():
            tokens = self.tokenizer([text]).to(self.device)
            features = self.model.encode_text(tokens)
            features /= features.norm(dim=-1, keepdim=True)
            return tuple(features[0].cpu().numpy().tolist())

    def encode_image(self, image_input: str | Path | Any) -> Vector:
        if not isinstance(image_input, self.Image.Image):
            image = self.Image.open(image_input).convert("RGB")
        else:
            image = image_input.convert("RGB")

        with self.torch.no_grad():
            tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            features = self.model.encode_image(tensor)
            features /= features.norm(dim=-1, keepdim=True)
            return tuple(features[0].cpu().numpy().tolist())

    def encode_roi(self, image_input: str | Path | Any, bbox: list[float]) -> Vector:
        if not isinstance(image_input, self.Image.Image):
            image = self.Image.open(image_input).convert("RGB")
        else:
            image = image_input.convert("RGB")

        if len(bbox) == 4:
            x, y, w, h = bbox
            crop_box = (max(0, int(x)), max(0, int(y)), max(0, int(x + w)), max(0, int(y + h)))
            if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                image = image.crop(crop_box)

        return self.encode_image(image)

    def _encode_pil_image_bytes(self, raw_bytes: bytes) -> Vector:
        """Decode raw image bytes to PIL Image and encode via CLIP."""
        image = self.Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        return self.encode_image(image)


class HashingTextEncoder(BaseMultimodalEncoder):
    """Deterministic feature-hashing text & visual encoder.

    Provides high-speed, lightweight encoding for testing & baseline fallback.
    """

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def tokenize(self, text: str) -> list[str]:
        return TOKEN_PATTERN.findall(text.lower())

    def encode_text(self, text: str) -> Vector:
        buckets = [0.0] * self.dim
        for token in self.tokenize(text):
            digest = hashlib.sha1(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            buckets[index] += sign
        return normalize(buckets)

    def encode_image(self, image_input: str | Path | Any) -> Vector:
        if isinstance(image_input, (str, Path)):
            text_repr = f"image {Path(image_input).name}"
        else:
            text_repr = "image visual content xray"
        return self.encode_text(text_repr)

    def encode_roi(self, image_input: str | Path | Any, bbox: list[float]) -> Vector:
        roi_str = f"roi lesion region bbox {bbox} " + (
            str(image_input) if isinstance(image_input, (str, Path)) else "crop"
        )
        return self.encode_text(roi_str)

    def _encode_pil_image_bytes(self, raw_bytes: bytes) -> Vector:
        """Encode raw image bytes via filename-text proxy for hashing encoder."""
        # Hashing encoder has no real vision; encode a representative text
        return self.encode_text("pasted xray bone image grayscale fracture")


def get_multimodal_encoder(mode: str = "auto") -> BaseMultimodalEncoder:
    """Return BiomedCLIPEncoder if mode=='biomedclip', else HashingTextEncoder."""
    if mode == "biomedclip":
        try:
            return BiomedCLIPEncoder()
        except Exception:
            pass
    if mode == "clip":
        try:
            return BiomedCLIPEncoder(model_name="ViT-B-32", pretrained="openai")
        except Exception:
            pass
    return HashingTextEncoder()


AVAILABLE_ENCODERS = {
    "hashing": {
        "label": "Hashing Encoder (Baseline)",
        "description": "Lightweight deterministic feature-hashing. No dependencies, instant startup.",
        "requires_download": False,
    },
    "biomedclip": {
        "label": "BiomedCLIP (Microsoft)",
        "description": "Biomedical CLIP from PubMed literature. Best for medical image understanding.",
        "requires_download": True,
        "download_size_mb": 400,
    },
    "clip": {
        "label": "CLIP ViT-B/32 (OpenAI)",
        "description": "General-purpose CLIP vision encoder. Lighter than BiomedCLIP.",
        "requires_download": True,
        "download_size_mb": 350,
    },
}
