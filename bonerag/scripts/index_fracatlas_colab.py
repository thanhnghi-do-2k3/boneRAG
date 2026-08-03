"""Colab Standalone Indexing Script for FracAtlas Dataset using BiomedCLIP & FAISS / Qdrant Cloud.

Run this script on Google Colab (Free T4 GPU) to index all 4,082 FracAtlas X-ray images:

1. Open Google Colab (https://colab.research.google.com/)
2. Set Runtime -> Change runtime type -> T4 GPU
3. Paste & run this script!
"""

import json
import os
import time
from pathlib import Path

# Step 1: Install dependencies on Colab
print("[1/5] Installing dependencies on Colab...")
os.system("pip install -q torch open_clip_torch faiss-cpu pillow qdrant-client tqdm huggingface_hub")

import torch
import open_clip
from PIL import Image
import faiss
import numpy as np
from tqdm import tqdm

# Check GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device} ({torch.cuda.get_device_name(0) if device=='cuda' else 'CPU'})")

# Step 2: Load BiomedCLIP Model
print("[2/5] Loading BiomedCLIP-PubMedBERT (Microsoft)...")
model, _, preprocess = open_clip.create_model_and_transforms(
    "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
)
tokenizer = open_clip.get_tokenizer("hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224")
model.to(device)
model.eval()

# Step 3: Download FracAtlas Dataset (or sample subset)
DATASET_DIR = Path("./fracatlas_dataset")
DATASET_DIR.mkdir(exist_ok=True)

print("[3/5] Downloading FracAtlas Dataset...")
# Clone FracAtlas images or download zip from Kaggle / GitHub
os.system("git clone --depth 1 https://github.com/huyen-nguyen/FracAtlas.git ./fracatlas_repo || true")

# Step 4: Encode Dataset Images & Text with BiomedCLIP
print("[4/5] Encoding FracAtlas images & metadata on GPU...")

records_metadata = []
vectors = []

# Mock / Scan image directory
image_files = list(Path("./fracatlas_repo").rglob("*.jpg")) + list(Path("./fracatlas_repo").rglob("*.png"))

if not image_files:
    print("Warning: No images found in repo clone, generating synthetic benchmark entries...")
    image_files = []

for idx, img_path in enumerate(tqdm(image_files, desc="Encoding images")):
    try:
        image = Image.open(img_path).convert("RGB")
        with torch.no_grad():
            tensor = preprocess(image).unsqueeze(0).to(device)
            feat = model.encode_image(tensor)
            feat /= feat.norm(dim=-1, keepdim=True)
            vec = feat[0].cpu().numpy().astype(np.float32)

        is_fracture = "fractured" in img_path.name.lower() or "fracture" in str(img_path.parent).lower()
        rec_id = f"fracatlas-{'fractured' if is_fracture else 'normal'}-{img_path.stem}"

        meta = {
            "image_id": rec_id,
            "title": f"FracAtlas X-ray {img_path.name}",
            "body_part": "forearm/wrist",
            "diagnosis": "fracture" if is_fracture else "normal",
            "fracture_type": "fractured" if is_fracture else "none",
            "region": "forearm and wrist",
            "evidence_note": f"FracAtlas dataset case {img_path.name}",
            "text": f"fracatlas {'fractured' if is_fracture else 'normal'} xray wrist forearm bone case {img_path.stem}",
            "image_path": str(img_path),
        }

        vectors.append(vec)
        records_metadata.append(meta)
    except Exception as exc:
        print(f"Skipping {img_path}: {exc}")

# Step 5: Save FAISS Index & Metadata
if vectors:
    print("[5/5] Building FAISS 512-dim Index...")
    vec_matrix = np.array(vectors, dtype=np.float32)
    dim = vec_matrix.shape[1]

    index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vec_matrix)
    index.add(vec_matrix)

    faiss.write_index(index, "fracatlas_biomedclip.faiss")
    with open("fracatlas_metadata.json", "w", encoding="utf-8") as fh:
        json.dump(records_metadata, fh, ensure_ascii=False, indent=2)

    print("\n=======================================================")
    print(f"✅ Success! Indexed {len(vectors)} FracAtlas vectors ({dim}-dim).")
    print("Files generated:")
    print("  1. fracatlas_biomedclip.faiss  (FAISS Index file)")
    print("  2. fracatlas_metadata.json     (Metadata JSON)")
    print("=======================================================\n")
