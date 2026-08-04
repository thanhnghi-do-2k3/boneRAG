"""Small Baseline knowledge base.

The real project will load FracAtlas/MURA/BTRXD records from disk. For Baseline
we keep a tiny in-code corpus so the retrieval pipeline and server run on any
machine without downloading datasets.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


@dataclass(frozen=True)
class ImageRecord:
    """One evidence item in the image knowledge base.

    In Baseline, `image_id` is a symbolic id rendered by the web UI. Later it can
    become a real image path. The `text` field is what the default encoder sees.
    """

    image_id: str
    title: str
    body_part: str
    diagnosis: str
    fracture_type: str
    region: str
    evidence_note: str
    text: str
    image_path: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    fracture_boxes: list[list[float]] | None = None


def _discover_dataset_images_root() -> Path | None:
    """Try to find the local FracAtlas-style image folder.

    Priority:
    1. BONERAG_DATASET_IMAGES_ROOT env var
    2. Common sibling folder next to this repository (../TH-P2/...)
    """

    env_path = os.environ.get("BONERAG_DATASET_IMAGES_ROOT", "").strip()
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.exists() and candidate.is_dir():
            return candidate

    repo_root = Path(__file__).resolve().parents[2]
    default_candidate = (repo_root.parent / "TH-P2" / "segmentation" / "dataset" / "images").resolve()
    if default_candidate.exists() and default_candidate.is_dir():
        return default_candidate

    return None


def _load_fracture_annotations(images_root: Path) -> dict[str, dict[str, object]]:
    """Return per-file fracture metadata from COCO annotations if available."""

    annotation_path = (
        images_root.parent
        / "Annotations"
        / "COCO JSON"
        / "COCO_fracture_masks.json"
    )
    if not annotation_path.exists():
        return {}

    try:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    image_meta_by_id: dict[int, dict[str, object]] = {}
    for image in payload.get("images", []):
        image_id = image.get("id")
        file_name = image.get("file_name")
        if not isinstance(image_id, int) or not isinstance(file_name, str):
            continue
        image_meta_by_id[image_id] = {
            "file_name": file_name,
            "width": int(image.get("width", 0)) if image.get("width") else None,
            "height": int(image.get("height", 0)) if image.get("height") else None,
            "fracture_boxes": [],
        }

    for ann in payload.get("annotations", []):
        image_id = ann.get("image_id")
        bbox = ann.get("bbox")
        if not isinstance(image_id, int) or not isinstance(bbox, list) or len(bbox) != 4:
            continue
        target = image_meta_by_id.get(image_id)
        if not target:
            continue
        target["fracture_boxes"].append([float(value) for value in bbox])

    by_file: dict[str, dict[str, object]] = {}
    for entry in image_meta_by_id.values():
        file_name = entry.get("file_name")
        if isinstance(file_name, str):
            by_file[file_name] = entry
    return by_file


def _build_dataset_sample_records() -> list[ImageRecord]:
    """Build many UI-friendly records from local FracAtlas folders."""

    images_root = _discover_dataset_images_root()
    if images_root is None:
        return []

    fractured_files = sorted((images_root / "Fractured").glob("*.jpg"))
    non_fractured_files = sorted((images_root / "Non_fractured").glob("*.jpg"))
    if not fractured_files and not non_fractured_files:
        return []

    limit_env = os.environ.get("BONERAG_RECORD_LIMIT", "").strip()
    limit = int(limit_env) if limit_env.isdigit() else max(len(fractured_files) + len(non_fractured_files), 4085)
    fractured_limit = min(len(fractured_files), max(1, int(limit * 0.65)))
    normal_limit = min(len(non_fractured_files), max(1, limit - fractured_limit))
    selected_fractured = fractured_files[:fractured_limit]
    selected_normal = non_fractured_files[:normal_limit]

    annotation_lookup = _load_fracture_annotations(images_root)

    records: list[ImageRecord] = []
    max_len = max(len(selected_fractured), len(selected_normal))
    for index in range(max_len):
        if index < len(selected_fractured):
            image_path = selected_fractured[index]
            ann = annotation_lookup.get(image_path.name, {})
            fracture_boxes = ann.get("fracture_boxes") if isinstance(ann, dict) else None
            records.append(
                ImageRecord(
                    image_id=f"fracatlas-fractured-{image_path.stem.lower()}",
                    title=f"FracAtlas fractured X-ray {image_path.stem}",
                    body_part="forearm/wrist",
                    diagnosis="fracture",
                    fracture_type="fractured",
                    region="forearm and wrist",
                    evidence_note=(
                        f"Real FracAtlas fractured case."
                        + (f" Annotated fracture regions: {len(fracture_boxes)}." if fracture_boxes else "")
                    ),
                    text=(
                        f"fracatlas fractured xray wrist forearm bone fracture case {image_path.stem.lower()}"
                    ),
                    image_path=str(image_path),
                    image_width=ann.get("width") if isinstance(ann, dict) else None,
                    image_height=ann.get("height") if isinstance(ann, dict) else None,
                    fracture_boxes=fracture_boxes if isinstance(fracture_boxes, list) and fracture_boxes else None,
                )
            )

        if index < len(selected_normal):
            image_path = selected_normal[index]
            records.append(
                ImageRecord(
                    image_id=f"fracatlas-normal-{image_path.stem.lower()}",
                    title=f"FracAtlas non-fractured X-ray {image_path.stem}",
                    body_part="forearm/wrist",
                    diagnosis="normal",
                    fracture_type="none",
                    region="forearm and wrist",
                    evidence_note="Real FracAtlas non-fractured reference case.",
                    text=f"fracatlas normal xray wrist forearm bone no fracture case {image_path.stem.lower()}",
                    image_path=str(image_path),
                )
            )

        if len(records) >= limit:
            break
    return records[:limit]


FALLBACK_RECORDS: list[ImageRecord] = [
    ImageRecord(
        image_id="frac-wrist-001",
        title="Distal radius fracture",
        body_part="wrist",
        diagnosis="fracture",
        fracture_type="transverse",
        region="distal radius metaphysis",
        evidence_note="Lucent fracture line near the distal radius with cortical disruption.",
        text=(
            "wrist distal radius transverse fracture xray lucent line cortical disruption "
            "metaphysis abnormal bone"
        ),
    ),
    ImageRecord(
        image_id="frac-hand-014",
        title="Fifth metacarpal fracture",
        body_part="hand",
        diagnosis="fracture",
        fracture_type="oblique",
        region="fifth metacarpal shaft",
        evidence_note="Oblique fracture line through the metacarpal shaft with mild displacement.",
        text=(
            "hand fifth metacarpal oblique fracture shaft displacement xray abnormal "
            "bone injury"
        ),
    ),
    ImageRecord(
        image_id="normal-wrist-022",
        title="Normal wrist reference",
        body_part="wrist",
        diagnosis="normal",
        fracture_type="none",
        region="carpal and distal forearm",
        evidence_note="No visible cortical break or displaced fragment in this reference image.",
        text="normal wrist xray no fracture intact cortex distal radius ulna carpal bones",
    ),
    ImageRecord(
        image_id="frac-hip-007",
        title="Femoral neck fracture",
        body_part="hip",
        diagnosis="fracture",
        fracture_type="impacted",
        region="femoral neck",
        evidence_note="Irregular lucency and trabecular interruption around the femoral neck.",
        text="hip femoral neck impacted fracture xray trabecular interruption lucency abnormal",
    ),
    ImageRecord(
        image_id="tumor-tibia-003",
        title="Aggressive tibial bone lesion",
        body_part="leg",
        diagnosis="bone lesion",
        fracture_type="pathologic risk",
        region="proximal tibia",
        evidence_note="Mixed lytic-sclerotic lesion with cortical thinning, suspicious for tumor-like pathology.",
        text="leg tibia bone tumor lesion lytic sclerotic cortical thinning pathologic xray",
    ),
    ImageRecord(
        image_id="normal-hip-019",
        title="Normal hip reference",
        body_part="hip",
        diagnosis="normal",
        fracture_type="none",
        region="pelvis and proximal femur",
        evidence_note="Smooth cortical outline and preserved joint alignment without fracture sign.",
        text="normal hip pelvis proximal femur xray no fracture preserved alignment cortex",
    ),
]


SAMPLE_RECORDS: list[ImageRecord] = _build_dataset_sample_records() or FALLBACK_RECORDS
