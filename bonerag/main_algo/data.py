"""Small Baseline knowledge base.

The real project will load FracAtlas/MURA/BTRXD records from disk. For Baseline
we keep a tiny in-code corpus so the retrieval pipeline and server run on any
machine without downloading datasets.
"""

from __future__ import annotations

from dataclasses import dataclass


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


SAMPLE_RECORDS: list[ImageRecord] = [
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
