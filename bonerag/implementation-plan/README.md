# Implementation plan

Plan thực hiện nằm trong `code/` để repo này có thể tách riêng và vẫn đủ ngữ cảnh triển khai.

## Milestone 0 - Baseline đang có

- Server Python chuẩn thư viện.
- React UI chat streaming.
- Evidence drawer/modal.
- Log runtime.
- Evaluation workspace.

## Milestone 1 - Dataset thật

- Chuẩn hóa loader FracAtlas/MURA/BTRXD.
- Tạo schema `ImageRecord` có đường dẫn ảnh thật, mask/ROI, body part, diagnosis, region.
- Tách train/val/test và ground truth evidence.

## Milestone 2 - Retriever hình ảnh thật

- Thay hashing encoder bằng BiomedCLIP hoặc encoder vision-language y sinh.
- Tạo embedding cho full image và ROI/crop.
- Thay index in-memory bằng FAISS.

## Milestone 3 - Rerank và evidence gate

- Thêm rerank theo body part, anatomy region, fracture finding.
- Thêm hard negative mining.
- Gate từ chối trả lời khi evidence yếu hoặc trái ngữ cảnh.

## Milestone 4 - Generator

- Thay template answer bằng MLLM.
- Bắt generator trích dẫn evidence.
- Thêm kiểm tra hallucination/factuality.

## Milestone 5 - Đánh giá

- Ghi từng lần chạy vào `evaluation/experiments.jsonl`.
- So sánh Recall@k, answer accuracy, faithfulness, latency.
- Chỉ giữ cải tiến khi metric tốt hơn baseline hoặc giảm lỗi rõ ràng.
