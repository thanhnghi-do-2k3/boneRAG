export const stageLabels = {
  start: 'Bắt đầu',
  encode: 'Encode',
  retrieve: 'Retrieve',
  gate: 'Gate',
  rerank: 'Rerank',
  done: 'Hoàn tất',
};

export const pipelineSteps = [
  ['Query', 'Người dùng nhập câu hỏi về ảnh X-quang xương.'],
  ['Encode', 'BiomedCLIP (PubMedBERT + ViT-B/16) mã hóa câu hỏi và hình ảnh thành vector đa phương thức.'],
  ['Retrieve', 'InMemoryVectorIndex lấy top-k case gần nhất.'],
  ['Gate', 'Cổng quyết định có dùng evidence hay không.'],
  ['Rerank', 'Cộng điểm body part, diagnosis và region.'],
  ['Answer', 'Template generator sinh câu trả lời kèm evidence.'],
];

export const welcomeMessage = {
  id: 'welcome',
  role: 'assistant',
  text:
    'Chào bạn, mình là BoneRAG. Hãy hỏi một câu về X-quang xương, mình sẽ stream câu trả lời và gắn evidence vào từng bong bóng chat.',
  evidence: [],
  status: 'done',
};

export const fallbackSampleRecords = [
  {
    image_id: "fracatlas-fractured-img0000019",
    title: "Distal radius fracture (Cổ tay)",
    body_part: "wrist",
    diagnosis: "fracture",
    fracture_type: "transverse",
    region: "distal radius metaphysis",
    evidence_note: "Gãy ngang đầu dưới xương quay cổ tay kèm mất liên tục vỏ xương.",
    image_url: "/api/image/fracatlas-fractured-img0000019",
  },
  {
    image_id: "fracatlas-fractured-img0000042",
    title: "Fifth metacarpal fracture (Bàn tay)",
    body_part: "hand",
    diagnosis: "fracture",
    fracture_type: "oblique",
    region: "fifth metacarpal shaft",
    evidence_note: "Gãy chéo thân xương bàn tay số 5 di lệch nhẹ.",
    image_url: "/api/image/fracatlas-fractured-img0000042",
  },
  {
    image_id: "fracatlas-normal-img0000105",
    title: "Normal wrist reference (Cổ tay bình thường)",
    body_part: "wrist",
    diagnosis: "normal",
    fracture_type: "none",
    region: "carpal and distal forearm",
    evidence_note: "Vỏ xương liên tục, không thấy đường gãy hay tổn thương xương.",
    image_url: "/api/image/fracatlas-normal-img0000105",
  },
  {
    image_id: "fracatlas-fractured-img0000210",
    title: "Femoral neck fracture (Cổ xương đùi)",
    body_part: "hip",
    diagnosis: "fracture",
    fracture_type: "impacted",
    region: "femoral neck",
    evidence_note: "Gãy cài vùng cổ xương đùi, biến dạng bè xương vùng khớp háng.",
    image_url: "/api/image/fracatlas-fractured-img0000210",
  },
  {
    image_id: "fracatlas-fractured-img0000315",
    title: "Aggressive tibial bone lesion (Xương chày)",
    body_part: "leg",
    diagnosis: "bone lesion",
    fracture_type: "pathologic risk",
    region: "proximal tibia",
    evidence_note: "Tổn thương khuyết xương vùng mâm chày nghi u xương/nang xương.",
    image_url: "/api/image/fracatlas-fractured-img0000315",
  },
  {
    image_id: "fracatlas-normal-img0000402",
    title: "Normal hip reference (Khớp háng bình thường)",
    body_part: "hip",
    diagnosis: "normal",
    fracture_type: "none",
    region: "femoral head and acetabulum",
    evidence_note: "Diện khớp háng trơn nhẵn, chỏm xương đùi và ổ cối nguyên vẹn.",
    image_url: "/api/image/fracatlas-normal-img0000402",
  },
];
