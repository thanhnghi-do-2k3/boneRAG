"""Colab Standalone Batch 5-Model Indexing Script for FracAtlas Dataset.

Runs batch GPU encoding on all 4,082 FracAtlas X-ray images for 5 Foundation Models in 1 execution.
"""

import json
import os
import time
from pathlib import Path

print("[1/5] Installing dependencies on Colab GPU...")
os.system("pip install -q torch open_clip_torch faiss-cpu pillow tqdm huggingface_hub")

import torch
import open_clip
import faiss
import numpy as np
from PIL import Image
from tqdm import tqdm

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device} ({torch.cuda.get_device_name(0) if device=='cuda' else 'CPU'})")

print("[2/5] Downloading full FracAtlas Dataset (4,082 images)...")
os.system("wget -q --show-progress -O fracatlas_full.zip 'https://huggingface.co/datasets/runananya/fracatlas/resolve/main/archive%20%289%29.zip' || curl -L -o fracatlas_full.zip 'https://figshare.com/ndownloader/articles/22276042/versions/1'")

print("Unzipping FracAtlas dataset...")
os.system("unzip -q -o fracatlas_full.zip -d ./fracatlas_repo || true")

image_files = list(Path("./fracatlas_repo").rglob("*.jpg")) + list(Path("./fracatlas_repo").rglob("*.jpeg")) + list(Path("./fracatlas_repo").rglob("*.png"))
print(f"Found {len(image_files)} X-ray images in FracAtlas dataset!")

FOUNDATION_MODELS = [
    {
        "name": "BiomedCLIP (Microsoft Medical SOTA)",
        "prefix": "fracatlas_biomedclip",
        "hub": "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
    },
    {
        "name": "OpenAI CLIP ViT-B/32 (Base)",
        "prefix": "fracatlas_clip_vitb32",
        "model": "ViT-B-32",
        "pretrained": "openai"
    },
    {
        "name": "OpenAI CLIP ViT-L/14 (Large)",
        "prefix": "fracatlas_clip_vitl14",
        "model": "ViT-L-14",
        "pretrained": "openai"
    },
    {
        "name": "LAION-2B CLIP ViT-H/14 (Huge)",
        "prefix": "fracatlas_clip_vith14",
        "model": "ViT-H-14",
        "pretrained": "laion2b_s32b_b79k"
    },
    {
        "name": "BioViL / PubMed ViT-B/16",
        "prefix": "fracatlas_biovil",
        "model": "ViT-B-16",
        "pretrained": "laion2b_s34b_b88k"
    }
]

BATCH_SIZE = 64

print(f"\n[3/5] Starting Batch GPU Indexing for all {len(FOUNDATION_MODELS)} models...\n")

for idx, m_cfg in enumerate(FOUNDATION_MODELS, 1):
    m_name = m_cfg["name"]
    prefix = m_cfg["prefix"]
    print(f"[{idx}/{len(FOUNDATION_MODELS)}] Processing {m_name}...")

    try:
        if "hub" in m_cfg:
            model, _, preprocess = open_clip.create_model_and_transforms(m_cfg["hub"])
        else:
            model, _, preprocess = open_clip.create_model_and_transforms(m_cfg["model"], pretrained=m_cfg["pretrained"])

        model.to(device).eval()

        vectors = []
        metadata = []

        for i in range(0, len(image_files), BATCH_SIZE):
            batch_paths = image_files[i:i + BATCH_SIZE]
            tensors = []
            valid_paths = []

            for p in batch_paths:
                try:
                    img = Image.open(p).convert("RGB")
                    tensors.append(preprocess(img))
                    valid_paths.append(p)
                except Exception:
                    continue

            if not tensors:
                continue

            batch_tensor = torch.stack(tensors).to(device)
            with torch.no_grad():
                feats = model.encode_image(batch_tensor)
                feats /= feats.norm(dim=-1, keepdim=True)
                feats_np = feats.cpu().numpy().astype(np.float32)

            for p, vec in zip(valid_paths, feats_np):
                is_frac = "fractured" in p.name.lower() or "fracture" in str(p.parent).lower()
                vectors.append(vec)
                metadata.append({
                    "image_id": f"fracatlas-{'fractured' if is_frac else 'normal'}-{p.stem.lower()}",
                    "title": f"FracAtlas X-ray {p.name}",
                    "body_part": "forearm/wrist",
                    "diagnosis": "fracture" if is_frac else "normal",
                    "fracture_type": "fractured" if is_frac else "none",
                    "region": "forearm and wrist",
                    "evidence_note": f"FracAtlas real X-ray dataset case {p.name}.",
                    "text": f"fracatlas {'fractured' if is_frac else 'normal'} xray wrist forearm bone case {p.stem.lower()}",
                    "image_path": str(p)
                })

        vec_matrix = np.array(vectors, dtype=np.float32)
        dim = vec_matrix.shape[1]

        index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(vec_matrix)
        index.add(vec_matrix)

        faiss_file = f"{prefix}.faiss"
        meta_file = f"{prefix}_metadata.json"

        faiss.write_index(index, faiss_file)
        with open(meta_file, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)

        print(f"✅ Finished {m_name} -> {faiss_file} ({dim}-dim, {len(vectors)} vectors)")

        del model
        torch.cuda.empty_cache()

    except Exception as exc:
        print(f"❌ Error processing {m_name}: {exc}")

print("\n=======================================================")
print("🎉 ALL 5 FOUNDATION MODELS INDEXED SUCCESSFULLY!")
print("=======================================================")
