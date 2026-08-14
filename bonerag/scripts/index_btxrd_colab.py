"""Colab batch indexing script for the BTXRD/BTRXD bone tumor X-ray dataset.

Outputs FAISS + metadata artifacts named ``btxrd_<encoder>.faiss`` and
``btxrd_<encoder>_metadata.json``. The script is intentionally dataset-layout
tolerant because Kaggle mirrors of BTXRD/BTRXD use slightly different folder
names.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_KAGGLE_DATASET = "thanhngan123/btxrd-data"
BATCH_SIZE = int(os.environ.get("BONERAG_INDEX_BATCH_SIZE", "64"))


FOUNDATION_MODELS = [
    {
        "name": "BiomedCLIP",
        "prefix": "btxrd_biomedclip",
        "hub": "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224",
    },
    {
        "name": "OpenAI CLIP ViT-B/32",
        "prefix": "btxrd_clip_vitb32",
        "model": "ViT-B-32",
        "pretrained": "openai",
    },
    {
        "name": "OpenAI CLIP ViT-L/14",
        "prefix": "btxrd_clip_vitl14",
        "model": "ViT-L-14",
        "pretrained": "openai",
    },
]


def run(command: list[str], check: bool = True) -> int:
    print("$ " + " ".join(command))
    result = subprocess.run(command, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    return result.returncode


def install_dependencies() -> None:
    print("[1/5] Installing dependencies...")
    run([
        "python3",
        "-m",
        "pip",
        "install",
        "-q",
        "torch",
        "open_clip_torch",
        "faiss-cpu",
        "pillow",
        "tqdm",
        "huggingface_hub",
        "pandas",
        "openpyxl",
        "kaggle",
    ])


def mount_drive() -> tuple[bool, Path, Path]:
    drive_dir = Path("/content/drive/MyDrive/BoneRAG_Data")
    index_store_dir = drive_dir / "indexes"
    try:
        from google.colab import drive  # type: ignore

        drive.mount("/content/drive", force_remount=False)
        index_store_dir.mkdir(parents=True, exist_ok=True)
        return True, drive_dir, index_store_dir
    except Exception:
        print("Drive is not mounted; artifacts will stay in the Colab runtime.")
        return False, drive_dir, Path("/content")


def _candidate_roots(drive_dir: Path) -> list[Path]:
    env_roots = [
        os.environ.get("BONERAG_BTXRD_ROOT", ""),
        os.environ.get("BTXRD_ROOT", ""),
        os.environ.get("BTRXD_ROOT", ""),
    ]
    roots = [Path(value).expanduser() for value in env_roots if value.strip()]
    roots.extend([
        Path("/content/btxrd-data"),
        Path("/content/btxrd_repo"),
        Path("/content/BTXRD"),
        Path("/content/BTRXD"),
        Path("/content/Bone Tumor X-ray Radiograph Dataset (BTXRD)"),
        Path("/content/btxrd_download"),
        drive_dir / "btxrd-data",
        drive_dir / "BTXRD",
        drive_dir / "BTRXD",
    ])
    return roots


def _has_images(path: Path) -> bool:
    return path.exists() and path.is_dir() and any(
        item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
        for item in path.rglob("*")
    )


def _extract_zip(zip_path: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {zip_path} -> {destination}")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)
    return destination


def _find_zip(drive_dir: Path) -> Path | None:
    env_zip = os.environ.get("BONERAG_BTXRD_ZIP", "") or os.environ.get("BTXRD_ZIP", "")
    candidates = [Path(env_zip).expanduser()] if env_zip.strip() else []
    candidates.extend([
        Path("/content/btxrd-data.zip"),
        Path("/content/btxrd.zip"),
        drive_dir / "btxrd-data.zip",
        drive_dir / "BTXRD.zip",
        drive_dir / "BTRXD.zip",
    ])
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _kaggle_credentials_available() -> bool:
    return (
        Path("/root/.kaggle/kaggle.json").exists()
        or (bool(os.environ.get("KAGGLE_USERNAME")) and bool(os.environ.get("KAGGLE_KEY")))
    )


def resolve_btxrd_root(drive_dir: Path) -> Path:
    print("[2/5] Locating BTXRD/BTRXD dataset...")
    drive_available = Path("/content/drive/MyDrive").exists()
    for root in _candidate_roots(drive_dir):
        if _has_images(root):
            print(f"Found BTXRD images at: {root}")
            return root

    zip_path = _find_zip(drive_dir)
    if zip_path:
        extract_dir = drive_dir / "btxrd-data" if drive_available else Path("/content/btxrd_repo")
        extracted = _extract_zip(zip_path, extract_dir)
        if _has_images(extracted):
            return extracted

    direct_url = os.environ.get("BONERAG_BTXRD_ZIP_URL", "") or os.environ.get("BTXRD_ZIP_URL", "")
    if direct_url:
        target_zip = drive_dir / "btxrd-data.zip" if drive_available else Path("/content/btxrd-data.zip")
        run(["curl", "-L", "-o", str(target_zip), direct_url])
        extract_dir = drive_dir / "btxrd-data" if drive_available else Path("/content/btxrd_repo")
        extracted = _extract_zip(target_zip, extract_dir)
        if _has_images(extracted):
            return extracted

    if _kaggle_credentials_available():
        dataset = os.environ.get("BTXRD_KAGGLE_DATASET", DEFAULT_KAGGLE_DATASET)
        target_dir = (
            drive_dir / "btxrd-data"
            if Path("/content/drive/MyDrive").exists()
            else Path("/content/btxrd_download")
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        run(["kaggle", "datasets", "download", "-d", dataset, "-p", str(target_dir), "--unzip"])
        if _has_images(target_dir):
            return target_dir

    raise SystemExit(
        "BTXRD/BTRXD dataset not found.\n"
        "Put the extracted dataset at /content/btxrd-data or "
        "/content/drive/MyDrive/BoneRAG_Data/btxrd-data, or set BONERAG_BTXRD_ROOT.\n"
        "Alternatively upload btxrd-data.zip to Drive/BoneRAG_Data, or set Kaggle "
        "credentials and BTXRD_KAGGLE_DATASET=thanhngan123/btxrd-data."
    )


def truthy(value: Any) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "1.0", "true", "yes", "y", "positive", "present"}


def normalized_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def infer_labels_from_path(image_path: Path) -> dict[str, str]:
    parts = {normalized_token(part) for part in image_path.parts}
    joined = "_".join(parts)
    if {"non_affected", "nonaffected", "normal", "non_tumor", "not_affected"} & parts:
        return {"diagnosis": "normal", "tumor_type": "none", "pathology": "none"}
    if "malignant" in joined:
        return {"diagnosis": "bone_tumor", "tumor_type": "malignant", "pathology": "malignant bone tumor"}
    if "benign" in joined:
        return {"diagnosis": "bone_tumor", "tumor_type": "benign", "pathology": "benign bone tumor"}
    if "tumor" in joined:
        return {"diagnosis": "bone_tumor", "tumor_type": "unknown", "pathology": "bone tumor"}
    return {"diagnosis": "unknown", "tumor_type": "unknown", "pathology": "unknown"}


def _row_image_keys(row: dict[str, Any]) -> list[str]:
    keys = []
    for key, value in row.items():
        text = str(value).strip()
        if not text:
            continue
        suffix = Path(text).suffix.lower()
        if suffix in IMAGE_EXTENSIONS or text.lower().startswith("img"):
            keys.extend([Path(text).name.lower(), Path(text).stem.lower()])
    return keys


def _read_table(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    if path.suffix.lower() in {".xlsx", ".xls"}:
        try:
            import pandas as pd

            return pd.read_excel(path).fillna("").to_dict(orient="records")
        except Exception as exc:
            print(f"Could not read {path}: {exc}")
    return []


def load_table_metadata(root: Path) -> dict[str, dict[str, Any]]:
    table_paths = list(root.rglob("dataset.csv")) + list(root.rglob("dataset.xlsx")) + list(root.rglob("*.csv"))
    metadata: dict[str, dict[str, Any]] = {}
    for table_path in table_paths:
        if any(part.lower() in {"annotations", "labels", "yolo", "pascalvoc"} for part in table_path.parts):
            continue
        rows = _read_table(table_path)
        if not rows:
            continue
        print(f"Loaded {len(rows)} metadata rows from {table_path}")
        for row in rows:
            row_norm = {normalized_token(str(key)): value for key, value in row.items()}
            diagnosis = "bone_tumor" if truthy(row_norm.get("tumor", "")) else "normal"
            tumor_type = "none"
            pathology = "none"
            if truthy(row_norm.get("malignant", "")):
                diagnosis, tumor_type, pathology = "bone_tumor", "malignant", "malignant bone tumor"
            elif truthy(row_norm.get("benign", "")):
                diagnosis, tumor_type, pathology = "bone_tumor", "benign", "benign bone tumor"
            elif diagnosis == "bone_tumor":
                tumor_type, pathology = "unknown", "bone tumor"

            body_flags = [
                "hand", "ulna", "radius", "humerus", "wrist", "elbow", "shoulder",
                "feet", "tibia", "fibula", "femur", "ankle", "knee", "pelvis", "hip",
            ]
            view_flags = ["frontal", "lateral", "oblique", "ap", "pa"]
            region_flags = ["upper_limb", "lower_limb", "pelvis"]
            body_parts = [flag.replace("_", " ") for flag in body_flags if truthy(row_norm.get(flag, ""))]
            views = [flag.replace("_", " ") for flag in view_flags if truthy(row_norm.get(flag, ""))]
            regions = [flag.replace("_", " ") for flag in region_flags if truthy(row_norm.get(flag, ""))]
            entry = {
                "diagnosis": diagnosis,
                "tumor_type": tumor_type,
                "pathology": pathology,
                "body_part": ", ".join(body_parts) if body_parts else "unlabeled anatomy",
                "view": ", ".join(views) if views else "unknown view",
                "region": ", ".join(regions or body_parts) if (regions or body_parts) else "unlabeled anatomy",
            }
            for key in _row_image_keys(row):
                metadata[key] = entry
    return metadata


def build_annotation_lookup(root: Path) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    for annotation_dir_name in ("Annotations", "annotations", "Annotation", "annotation"):
        annotation_dir = next((path for path in root.rglob(annotation_dir_name) if path.is_dir()), None)
        if not annotation_dir:
            continue
        for path in annotation_dir.rglob("*.json"):
            lookup.setdefault(path.stem.lower(), path)
    return lookup


def boxes_from_labelme(path: Path | None) -> tuple[int | None, int | None, list[list[float]]]:
    if not path:
        return None, None, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None, []
    width = payload.get("imageWidth") or payload.get("width")
    height = payload.get("imageHeight") or payload.get("height")
    boxes: list[list[float]] = []
    for shape in payload.get("shapes", []):
        points = shape.get("points") if isinstance(shape, dict) else None
        if not isinstance(points, list) or not points:
            continue
        xs = [float(point[0]) for point in points if isinstance(point, list) and len(point) >= 2]
        ys = [float(point[1]) for point in points if isinstance(point, list) and len(point) >= 2]
        if xs and ys:
            boxes.append([min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)])
    for ann in payload.get("annotations", []):
        bbox = ann.get("bbox") if isinstance(ann, dict) else None
        if isinstance(bbox, list) and len(bbox) == 4:
            try:
                numeric_bbox = [float(value) for value in bbox]
            except (TypeError, ValueError):
                continue
            if all(math.isfinite(value) for value in numeric_bbox):
                boxes.append(numeric_bbox)
    return (
        int(width) if str(width).isdigit() else None,
        int(height) if str(height).isdigit() else None,
        boxes,
    )


def discover_image_files(root: Path) -> list[Path]:
    excluded = {"annotations", "annotation", "labels", "masks", "mask", "yolo", "pascalvoc"}
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        if any(normalized_token(part) in excluded for part in path.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: str(item).lower())


def build_metadata(root: Path, image_files: list[Path]) -> list[dict[str, Any]]:
    table_lookup = load_table_metadata(root)
    annotation_lookup = build_annotation_lookup(root)
    metadata = []
    for path in image_files:
        path_labels = infer_labels_from_path(path)
        row_labels = (
            table_lookup.get(path.name.lower())
            or table_lookup.get(path.stem.lower())
            or {}
        )
        labels = {**path_labels, **row_labels}
        diagnosis = str(labels.get("diagnosis", "unknown"))
        tumor_type = str(labels.get("tumor_type", "unknown"))
        body_part = str(labels.get("body_part", "unlabeled anatomy"))
        region = str(labels.get("region", body_part))
        width, height, tumor_boxes = boxes_from_labelme(annotation_lookup.get(path.stem.lower()))
        image_id = f"btxrd-{diagnosis.replace('_', '-')}-{tumor_type.replace('_', '-')}-{path.stem.lower()}"
        metadata.append({
            "dataset": "BTXRD",
            "image_id": image_id,
            "title": f"BTXRD bone tumor X-ray {path.name}",
            "body_part": body_part,
            "diagnosis": diagnosis,
            "fracture_type": "none",
            "tumor_type": tumor_type,
            "pathology": labels.get("pathology", "bone tumor" if diagnosis == "bone_tumor" else "none"),
            "region": region,
            "view": labels.get("view", "unknown view"),
            "evidence_note": (
                f"BTXRD/BTRXD bone tumor radiograph case {path.name}; "
                f"diagnosis={diagnosis}; tumor_type={tumor_type}."
                + (f" Annotated tumor regions: {len(tumor_boxes)}." if tumor_boxes else "")
            ),
            "text": (
                f"btxrd bone xray radiograph {diagnosis} {tumor_type} "
                f"{body_part} {region} {path.stem.lower()}"
            ),
            "image_path": str(path),
            "image_width": width,
            "image_height": height,
            "fracture_boxes": None,
            "tumor_boxes": tumor_boxes or None,
        })
    return metadata


def encode_indexes(image_files: list[Path], metadata: list[dict[str, Any]], index_store_dir: Path) -> None:
    import faiss
    import numpy as np
    import open_clip
    import torch
    from PIL import Image
    from tqdm import tqdm

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[3/5] Using device: {device} ({torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU'})")
    print(f"[4/5] Encoding {len(image_files)} BTXRD/BTRXD images with {len(FOUNDATION_MODELS)} models...")
    index_store_dir.mkdir(parents=True, exist_ok=True)

    for index, model_cfg in enumerate(FOUNDATION_MODELS, start=1):
        print(f"\n[{index}/{len(FOUNDATION_MODELS)}] Processing {model_cfg['name']}")
        if "hub" in model_cfg:
            model, _, preprocess = open_clip.create_model_and_transforms(model_cfg["hub"])
        else:
            model, _, preprocess = open_clip.create_model_and_transforms(
                model_cfg["model"],
                pretrained=model_cfg["pretrained"],
            )
        model.to(device).eval()
        vectors = []
        valid_metadata = []
        for start in tqdm(range(0, len(image_files), BATCH_SIZE)):
            batch_paths = image_files[start : start + BATCH_SIZE]
            tensors = []
            batch_metadata = []
            for path, item in zip(batch_paths, metadata[start : start + BATCH_SIZE]):
                try:
                    image = Image.open(path).convert("RGB")
                    tensors.append(preprocess(image))
                    batch_metadata.append(item)
                except Exception as exc:
                    print(f"Skipping unreadable image {path}: {exc}")
            if not tensors:
                continue
            batch_tensor = torch.stack(tensors).to(device)
            with torch.no_grad():
                features = model.encode_image(batch_tensor)
                features /= features.norm(dim=-1, keepdim=True)
                features_np = features.cpu().numpy().astype(np.float32)
            vectors.extend(features_np)
            valid_metadata.extend(batch_metadata)

        if not vectors:
            raise RuntimeError(f"No vectors produced for {model_cfg['name']}")

        matrix = np.asarray(vectors, dtype=np.float32)
        faiss.normalize_L2(matrix)
        faiss_index = faiss.IndexFlatIP(matrix.shape[1])
        faiss_index.add(matrix)

        faiss_file = Path("/content") / f"{model_cfg['prefix']}.faiss"
        metadata_file = Path("/content") / f"{model_cfg['prefix']}_metadata.json"
        faiss.write_index(faiss_index, str(faiss_file))
        metadata_file.write_text(json.dumps(valid_metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        faiss_dest = index_store_dir / faiss_file.name
        metadata_dest = index_store_dir / metadata_file.name
        if faiss_file.resolve() != faiss_dest.resolve():
            shutil.copy2(faiss_file, faiss_dest)
        if metadata_file.resolve() != metadata_dest.resolve():
            shutil.copy2(metadata_file, metadata_dest)
        print(
            f"Saved {faiss_file.name} and {metadata_file.name} "
            f"({len(valid_metadata)} images, dim={matrix.shape[1]})"
        )

        del model
        if device == "cuda":
            torch.cuda.empty_cache()


def main() -> None:
    started = time.time()
    install_dependencies()
    _, drive_dir, index_store_dir = mount_drive()
    root = resolve_btxrd_root(drive_dir)
    image_files = discover_image_files(root)
    if not image_files:
        raise SystemExit(f"No X-ray images found under {root}")
    print(f"Found {len(image_files)} BTXRD/BTRXD X-ray images.")
    metadata = build_metadata(root, image_files)
    label_counts: dict[str, int] = {}
    for item in metadata:
        key = f"{item['diagnosis']}:{item.get('tumor_type', 'unknown')}"
        label_counts[key] = label_counts.get(key, 0) + 1
    print("Label counts:", label_counts)
    encode_indexes(image_files, metadata, index_store_dir=index_store_dir)
    print("\nDone. BTXRD artifacts are in:")
    print("  /content/btxrd_*.faiss")
    print("  /content/btxrd_*_metadata.json")
    print(f"  {index_store_dir}/btxrd_*")
    print(f"Elapsed: {(time.time() - started) / 60:.1f} min")


if __name__ == "__main__":
    main()
