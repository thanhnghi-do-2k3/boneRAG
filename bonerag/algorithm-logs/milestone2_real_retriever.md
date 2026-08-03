# Milestone 2 Algorithm Log - Real Multimodal & FAISS Retriever

> **Ngày thực hiện**: 2026-08-03
> **Trạng thái**: Hoàn tất (Completed)

---

## 1. Tóm tắt các thay đổi (What Was Done)

### A. Multimodal & BiomedCLIP Encoder Abstraction (`bonerag/main_algo/encoder.py`)
- Định nghĩa lớp cơ sở `BaseMultimodalEncoder` chuẩn hóa 3 phương thức:
  - `encode_text(text: str) -> Vector`: Mã hóa câu hỏi / metadata văn bản.
  - `encode_image(image_input) -> Vector`: Mã hóa toàn bộ ảnh X-quang (`full_image`).
  - `encode_roi(image_input, bbox) -> Vector`: Cắt vùng nghi ngờ gãy xương theo bounding box `[x, y, w, h]` và mã hóa vùng tổn thương (`roi_crop`).
- Triển khai `BiomedCLIPEncoder`: Tự động nạp model `microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224` qua `open_clip` / PyTorch (với fallback tự động sang `ViT-B-32` nếu gặp sự cố mạng).
- Triển khai `HashingTextEncoder`: Encoder siêu nhẹ cho môi trường CPU / thử nghiệm nhanh không cần trọng số model.

### B. FAISS Vector Index Integration (`bonerag/main_algo/vector_index.py`)
- Triển khai `FAISSVectorIndex`: Sử dụng `faiss.IndexFlatIP` (Cosine Similarity trên vector chuẩn hóa L2).
- Cung cấp hàm khởi tạo `get_vector_index(dim)`: Tự động dùng `FAISSVectorIndex` nếu package `faiss-cpu` / `faiss` được cài đặt trên server, hoặc tự động fallback sang `InMemoryVectorIndex`.

### C. Multi-level Indexing & Retrieval (`bonerag/main_algo/pipeline.py`)
- **Offline Indexing Phase**: Mã hóa đa tầng cho mỗi record:
  1. `record.image_id`: Vector văn bản metadata.
  2. `record.image_id#image`: Vector toàn bộ ảnh X-quang.
  3. `record.image_id#roi_k`: Vector từng vùng tổn thương gãy xương (crop ROI).
- **Online Retrieval Phase**: Truy xuất song song trên toàn bộ index đa tầng, tự động khớp (merge) về record cha và lưu vết thông tin debug (`encoder_type`, `index_type`, `raw_hits`).

---

## 2. Yêu cầu Setup trên Server (Server Setup Requirements)

Hệ thống đã được thiết kế **tự động tương thích (backward-compatible)** với cả chế độ nhẹ (Lightweight/CPU) lẫn chế độ ML chuyên sâu (GPU/BiomedCLIP + FAISS).

### Để bật đầy đủ chế độ BiomedCLIP & Index FAISS tốc độ cao trên Server:

```bash
# 1. Cài đặt thư viện FAISS và PyTorch / OpenCLIP
pip install faiss-cpu open_clip_torch torch torchvision Pillow

# 2. Khởi động lại Server Demo (Port 8088)
python3 demo-app/server.py --port 8088
```

### Các gói phụ thuộc đã xác minh trong môi trường:
- `torch`: **Đã có sẵn** (AVAILABLE)
- `PIL`: **Đã có sẵn** (AVAILABLE)
- `open_clip`: **Đã có sẵn** (AVAILABLE)
- `faiss-cpu`: *Tùy chọn* (Nếu chưa cài `faiss-cpu`, hệ thống sẽ dùng `InMemoryVectorIndex` mà không gây ra lỗi).
