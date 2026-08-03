# BoneRAG: Medical Visual Question Answering for Bone Pathology & Fracture Detection using Multi-level Image RAG

![BoneRAG Demo](https://img.shields.io/badge/Status-Milestone%202%20Completed-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![React](https://img.shields.io/badge/React-19-blue)
![License](https://img.shields.io/badge/License-MIT-green)

**BoneRAG** là hệ thống Hỏi đáp thị giác Y khoa (Medical VQA) chuyên biệt cho chẩn đoán bệnh lý xương và phát hiện gãy xương từ ảnh X-quang, áp dụng kỹ thuật **Multi-level Image Retrieval-Augmented Generation (Image RAG)**.

---

## 📌 Cấu trúc dự án (Repository Architecture)

```text
BoneRAG/
├── .agents/                    # [AI Agent Setup & Context]
│   ├── AGENTS.md               # Quy tắc hoạt động & tiết kiệm token cho AI Agent
│   └── CODEBASE_MAP.md         # Bản đồ mã nguồn chi tiết & danh sách hàm
├── bonerag/                    # [Core Algorithm Package]
│   ├── main_algo/              # Thuật toán cốt lõi (data, encoder, index, pipeline)
│   ├── tests/                  # Unit tests cho bộ thuật toán
│   ├── evaluation/             # Lưu kết quả thử nghiệm & metrics
│   ├── algorithm-logs/         # Log lịch sử nâng cấp thuật toán (Milestone 2 log)
│   └── implementation-plan/    # Lộ trình triển khai 5 Milestones
├── demo-app/                   # [Fullstack Demo Application]
│   ├── server.py               # Python HTTP + SSE streaming backend (Port 8088)
│   ├── frontend/               # React 19 + Vite UI (Copy ảnh PNG Blob clipboard, Evidence drawer)
│   └── web/                    # Built static web files
├── research-server/            # [Research Hub Dashboard]
│   └── src/research-data.js    # Data khảo sát 12+ bài báo khoa học (VisRAG, RULE, MMed-RAG...)
└── papers/                     # [PDF Papers Library]
    ├── original/               # Papers gốc (VisRAG, Visual-RAG, Enhanced MM RAG-LLM...)
    └── additional/             # Papers mở rộng (EVisRAG, mKG-RAG, Utility Selection...)
```

---

## 🎯 Tiến độ triển khai (Milestones Progress)

- [x] **Milestone 0 - Baseline Framework**: Khung Server Python tiêu chuẩn, React UI streaming SSE, Evidence Drawer/Modal, Runtime logs.
- [x] **Milestone 1 - Dataset thật**: Nạp dữ liệu dataset **FracAtlas** (4.083 ảnh X-quang, nhãn gãy/không gãy, tọa độ COCO bounding box & mask phân đoạn).
- [x] **Milestone 2 - Multimodal BiomedCLIP & FAISS Retriever**:
  - Mã hóa đa phương thức y sinh (`BiomedCLIPEncoder` qua `open_clip` / PyTorch với fallback `HashingTextEncoder`).
  - Index vector tốc độ cao (`FAISSVectorIndex` dựa trên `faiss.IndexFlatIP` với fallback `InMemoryVectorIndex`).
  - Truy xuất đa tầng (Multi-level Retrieval): Mã hóa & tìm kiếm song song trên **Full Image**, **ROI Fracture Crops**, và **Text Metadata**.
- [ ] **Milestone 3 - Rerank & Evidence Gate**: Reranker loại bỏ hard negative theo vùng cơ thể, Cổng từ chối (Refusal gate) khi bằng chứng yếu.
- [ ] **Milestone 4 - MLLM Generator**: Tích hợp mô hình MLLM (Qwen2.5-VL / LLaVA-Med) sinh câu trả lời có grounding.
- [ ] **Milestone 5 - Evaluation**: Thực nghiệm & đánh giá toàn diện (Recall@k, Hit@k, Accuracy, Faithfulness, Latency).

---

## 🛠️ Hướng dẫn cài đặt & Chạy ứng dụng (Execution Guide)

### 1. Cài đặt môi trường Python (Server Setup)

Để chạy đầy đủ chế độ BiomedCLIP & FAISS Vector Index:
```bash
pip install faiss-cpu open_clip_torch torch torchvision Pillow
```
*(Lưu ý: Hệ thống đã được thiết kế tự động fallback sang chế độ nhẹ nếu chưa cài đặt `faiss-cpu`)*.

### 2. Chạy Unit Tests thuật toán

```bash
python3 -m unittest discover -s bonerag/tests
```
> Output mong đợi: `Ran 5 tests in 0.061s - OK`

### 3. Build & Chạy Demo App (Port 8088)

```bash
# Build React Frontend
cd demo-app/frontend
npm install
npm run build

# Quay lại thư mục gốc và chạy Server
cd ../..
python3 demo-app/server.py --port 8088
```
Mở trình duyệt truy cập: **[http://localhost:8088](http://localhost:8088)**

### 4. Chạy Research Hub (Port 5173)

```bash
cd research-server
npm install
npm run dev
```
Mở trình duyệt truy cập: **[http://localhost:5173](http://localhost:5173)**

---

## 📖 Tài liệu tham khảo & AI Context Guide

- **Bản đồ mã nguồn chi tiết**: [`.agents/CODEBASE_MAP.md`](file://.agents/CODEBASE_MAP.md)
- **Quy tắc làm việc cho AI Agent**: [`.agents/AGENTS.md`](file://.agents/AGENTS.md)
- **Log thuật toán Milestone 2**: [`bonerag/algorithm-logs/milestone2_real_retriever.md`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/algorithm-logs/milestone2_real_retriever.md)
- **Lộ trình chi tiết**: [`bonerag/implementation-plan/README.md`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/implementation-plan/README.md)
