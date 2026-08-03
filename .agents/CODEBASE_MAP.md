# BoneRAG Codebase Map & AI Context Guide

> **Mục đích**: File log kiến trúc và danh sách hàm để trợ lý AI (và lập trình viên) nắm bắt mã nguồn nhanh chóng, duy trì ngữ cảnh nhất quán và tiết kiệm tối đa token khi làm việc.

---

## 1. Cấu trúc tổng quan dự án (Directory Overview)

```text
BoneRAG/
├── .agents/                    # [AI Context & Rules]
│   ├── AGENTS.md               # Quy tắc hoạt động cho AI Agent
│   └── CODEBASE_MAP.md         # Bản đồ mã nguồn chi tiết (File này)
├── bonerag/                    # [Core Algorithm Package]
│   ├── main_algo/              # Thuật toán cốt lõi (data, encoder, index, pipeline)
│   ├── tests/                  # Unit tests cho pipeline
│   ├── evaluation/             # Lưu kết quả thử nghiệm & metrics
│   ├── algorithm-logs/         # Log thay đổi thuật toán
│   └── implementation-plan/    # Lộ trình triển khai 5 Milestones
├── demo-app/                   # [Fullstack Demo App]
│   ├── server.py               # HTTP Server (Stdlib Python, SSE streaming, REST API)
│   ├── frontend/               # UI React + Vite
│   └── web/                    # Built static files
├── research-server/            # [Research Hub Dashboard]
│   └── src/research-data.js    # Data khảo sát 12+ bài báo khoa học, pipeline & roadmap
└── papers/                     # [PDF Papers Library]
    ├── original/               # Papers gốc (VisRAG, Visual-RAG, Enhanced MM RAG-LLM...)
    └── additional/             # Papers mở rộng (EVisRAG, mKG-RAG, Utility Selection...)
```

---

## 2. Chi tiết Thuật toán Cốt lõi (`bonerag/main_algo/`)

### 📄 `bonerag/main_algo/data.py`
- **Data Schemas**:
  - `ImageRecord`: Dataclass mô tả 1 mẫu ảnh X-quang.
    - Fields: `image_id`, `title`, `body_part`, `diagnosis`, `fracture_type`, `region`, `evidence_note`, `text`, `image_path`, `image_width`, `image_height`, `fracture_boxes`.
- **Functions**:
  - `_discover_dataset_images_root() -> Path | None`: Tự động tìm thư mục dataset FracAtlas (`BONERAG_DATASET_IMAGES_ROOT` hoặc `../TH-P2/...`).
  - `_load_fracture_annotations(images_root: Path) -> dict`: Nạp tọa độ bounding box gãy xương từ COCO JSON masks.
  - `_build_dataset_sample_records() -> list[ImageRecord]`: Nạp danh sách mẫu từ dataset FracAtlas thật.
  - `FALLBACK_RECORDS`: 4 mẫu mock cố định khi chưa có dữ liệu FracAtlas thật.
  - `SAMPLE_RECORDS`: Tự động chọn dữ liệu FracAtlas hoặc fallback.

### 📄 `bonerag/main_algo/encoder.py`
- **Classes / Functions**:
  - `Vector`: Type alias `tuple[float, ...]`.
  - `normalize(values: list[float]) -> Vector`: Chuẩn hóa vector độ dài đơn vị (Dot product = Cosine similarity).
  - `HashingTextEncoder(dim: int = 256)`:
    - `tokenize(text: str) -> list[str]`: Tách từ bằng regex `[a-z0-9]+`.
    - `encode(text: str) -> Vector`: Feature-hashing SHA-1 phân bổ từ vào 256 buckets với sign +1/-1.
    - *Lưu ý*: Ý định tương lai là thay bằng **BiomedCLIP** / **VLM2Vec**.

### 📄 `bonerag/main_algo/vector_index.py`
- **Classes / Functions**:
  - `SearchHit`: Dataclass (`record_id`, `score`).
  - `dot(left, right) -> float`: Tích vô hướng 2 vector.
  - `InMemoryVectorIndex`:
    - `add(record_id: str, vector: Vector)`: Lưu vector vào dict in-memory.
    - `search(query_vector: Vector, top_k: int = 4) -> list[SearchHit]`: Tìm top-k cosine similarity.

### 📄 `bonerag/main_algo/pipeline.py`
- **Classes / Functions**:
  - `Evidence`: Dataclass thông tin bằng chứng được gán rerank score.
  - `BoneRAGResult`: Kết quả trả về (`question`, `used_retrieval`, `evidence`, `answer`, `debug`).
  - `BoneRAGPipeline`:
    - `records_as_dicts() -> list[dict]`: Xuất danh sách records dạng JSON.
    - `retrieve(question: str) -> list[SearchHit]`: Encode câu hỏi & truy xuất top-k ứng viên từ vector index.
    - `rerank(question: str, hits: list[SearchHit]) -> list[Evidence]`: Thêm điểm ưu tiên nếu trùng `body_part` hoặc từ khóa gãy xương.
    - `generate_answer(question: str, evidence: list[Evidence]) -> str`: Sinh câu trả lời có grounding/dẫn chứng.
    - `stream_answer(question: str) -> Generator[dict, None, None]`: Sinh câu trả lời theo luồng SSE events (`stage`, `token`, `done`, `error`).

---

## 3. Demo Server (`demo-app/server.py`)

- **Server Tech**: Python Standard Library (`ThreadingHTTPServer`, `BaseHTTPRequestHandler`).
- **Port Mặc định**: `8088`.
- **API Routes chính**:
  - `GET /api/records`: Trả về danh sách `ImageRecord` công khai.
  - `GET /api/answer-stream?question=...`: Server-Sent Events (SSE) streaming quá trình suy luận & câu trả lời.
  - `GET /api/image/<image_id>`: Serve file ảnh thật từ ổ đĩa địa phương.
  - Static Server: Serve React UI từ `demo-app/frontend/dist` hoặc `demo-app/web`.

---

## 4. Demo Frontend (`demo-app/frontend/src/`)

- **Framework**: React 19 + Vite (Vanilla CSS).
- **Core Architecture**:
  - `App.jsx`: State orchestrator (`chatReducer`), quản lý phiên, stream `EventSource`, paste ảnh từ clipboard (`selectPastedImage`).
  - `services/boneragApi.js`: Calls `/api/records` & mở `EventSource('/api/answer-stream')`.
  - `services/historyStorage.js`: Persist lịch sử phiên làm việc vào `localStorage`.
- **Views**:
  - `QuestionScreen.jsx`: Khung chat chính + composer + evidence drawer.
  - `ImageLibraryScreen.jsx`: Thư viện case mẫu. Chứa hàm `copyRecordImage()` copy ảnh dạng **PNG Blob** vào `navigator.clipboard.write` & `copyRecordDescription()`.
  - `LogScreen.jsx`: Debug log thời gian thực các giai đoạn pipeline.
  - `PipelineScreen.jsx`: Trực quan hóa kiến trúc Off-line & On-line pipeline.
  - `EvaluationScreen.jsx`: Bảng theo dõi kết quả đánh giá thử nghiệm.
  - `HistoryScreen.jsx`: Quản lý các phiên chat cũ.
- **Components**:
  - `ChatComposer.jsx`: Ô nhập liệu hỗ trợ dán ảnh trực tiếp (`onPaste`).
  - `ChatMessage.jsx`: Bong bóng tin nhắn câu hỏi / câu trả lời.
  - `EvidenceDrawer.jsx` & `EvidenceModal.jsx`: Thanh bên & Modal xem chi tiết bằng chứng + bounding box gãy xương (`fracture_boxes`).
  - `XrayPreview.jsx`: Component hiển thị ảnh X-quang hoặc fallback tile.

---

## 5. Research Server (`research-server/src/`)

- **File chính**: `src/research-data.js`
- **Nội dung lưu trữ**:
  - `papers`: Khảo sát chi tiết 12+ bài báo khoa học (*RULE*, *MMed-RAG*, *FactMM-RAG*, *VisRAG*, *RegionRAG*, *EVisRAG*, *mKG-RAG*, *FracAtlas*...).
  - `basicSteps`: 6 bước thiết lập bài toán VQA X-quang.
  - `pipelineGroups`: Sơ đồ các bước Off-line (D1-D4) và On-line (Q1-Q5).
  - `improvementIdeas`: Danh sách 6 hướng cải tiến (ROI retrieval, Utility rerank, Hard-negative fine-tuning...).
  - `comparisonRows`: Bảng so sánh 6 trục giữa Baseline vs Proposed BoneRAG.
  - `roadmap`: Lộ trình 4 mốc thời gian Milestone.

---

## 6. Lệnh Chạy Quick Reference (Commands)

```bash
# 1. Chạy Unit Tests thuật toán
python3 -m unittest discover -s bonerag/tests

# 2. Build & Chạy Demo App (Port 8088)
cd demo-app/frontend && npm run build
cd ../..
python3 demo-app/server.py --port 8088

# 3. Chạy Research Hub (Port 5173)
cd research-server
npm run dev
```

---

## 7. Tiết kiệm Token & Nguyên tắc làm việc cho AI Agent

1. **Đọc file này trước khi nghiên cứu lại từ đầu**: Đã nắm rõ luồng pipeline và danh sách các hàm, không cần đọc toàn bộ codebase khi sửa đổi nhỏ.
2. **Tuân thủ quy tắc Git**:
   - Thư mục nặng (`node_modules`, `dist`, `.venv`, `__pycache__`) bắt buộc nằm trong `.gitignore`.
   - Không commit file nhị phân lớn hoặc build artefacts.
3. **Giữ nguyên hợp đồng API**:
   - Khi chỉnh sửa `ImageRecord` hoặc `Evidence`, luôn đồng bộ giữa `bonerag/main_algo`, `demo-app/server.py` và React Frontend.
