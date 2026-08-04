# 📝 Agent Self-Correction & Refactoring Audit Log

File log ghi nhận toàn bộ lịch sử tự phát hiện lỗi, nguyên nhân, chi tiết sửa đổi và kết quả thu được của AI Agent trong quá trình phát triển hệ thống **BoneRAG**.

---

## 📌 Quy tắc ghi Log (Format Standard):
Mỗi lần Agent phát hiện sai sót / sửa đổi thuật toán, một entry sẽ được tự động ghi vào đây với cấu trúc:
- ⏱️ **Thời gian (Timestamp)**
- ❓ **Lý do sửa (Reason for Fix)**
- 🔍 **Nguyên nhân lỗi (Root Cause)**
- 🛠️ **Những gì đã sửa (Changes Applied)**
- ✅ **Kết quả thu được (Outcome & Verification)**

---

## 📜 Nhật ký sửa đổi (Audit Entries):

### [2026-08-04] Entry #005 - Triển khai Milestone 3: Anatomical Reranker, Hard Negative Mining & Evidence Gate
- ⏱️ **Thời gian**: 2026-08-04T14:15:00Z
- ❓ **Lý do sửa**: Cần hoàn thiện Milestone 3 nhằm nâng cao độ chính xác sắp xếp bằng chứng y khoa và từ chối các câu hỏi không thuộc miền ngữ cảnh X-quang.
- 🔍 **Nguyên nhân lỗi**: Thuật toán Reranking cũ chỉ tính overlap từ đơn giản; Cổng từ chối cũ chưa tự động lọc các câu hỏi tổng quát phi y tế (out-of-domain).
- 🛠️ **Những gì đã sửa**:
  1. Tạo module [`bonerag/main_algo/reranker.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/main_algo/reranker.py) kết hợp Cosine Similarity, Anatomical Alignment, Pathology Matching và phạt điểm Hard Negative.
  2. Tạo module [`bonerag/main_algo/gating.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/main_algo/gating.py) kiểm duyệt ngưỡng an toàn và lọc Out-of-Domain.
  3. Bổ sung bộ unit test [`test_milestone3_rerank_gate.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/tests/test_milestone3_rerank_gate.py).
- ✅ **Kết quả thu được**: Pass 100% 10 unit tests, Benchmark đạt Diagnosis Accuracy = 100%, Faithfulness = 75%, Latency giảm xuống **67.25 ms**.

---

### [2026-08-04] Entry #004 - Sửa thuật toán trích xuất Parent ID trong Benchmark Suite
- ⏱️ **Thời gian**: 2026-08-04T13:50:00Z
- ❓ **Lý do sửa**: Lần đầu chạy `run_benchmark.py`, chỉ số Recall@4 và MRR bị trả về `0.0000`.
- 🔍 **Nguyên nhân lỗi**: Kết quả truy xuất thô (`raw_hits`) trả về ID mẫu đính kèm suffix đa tầng (ví dụ `frac-wrist-001#text_metadata` hoặc `frac-wrist-001#crop_roi_0`), khiến bộ so khớp không nhận diện được `frac-wrist-001` trong Ground Truth.
- 🛠️ **Những gì đã sửa**: Thêm xử lý `raw_id.split("#")[0]` trong [`bonerag/evaluation/run_benchmark.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/evaluation/run_benchmark.py) để lấy chính xác ID gốc của ca bệnh cha.
- ✅ **Kết quả thu được**: Chạy lại Benchmark đo chính xác Recall@4 = 0.2500, MRR = 0.0833, Diagnosis Accuracy = 1.0000 (100%), Faithfulness = 0.7500 (75%), Latency = 94.5 ms.

---

### [2026-08-04] Entry #003 - Xử lý ngắt kết nối mềm (Graceful Socket & Pipe) cho Server Demo
- ⏱️ **Thời gian**: 2026-08-04T13:40:00Z
- ❓ **Lý do sửa**: Khi đổi cấu hình mô hình hoặc F5 trình duyệt, server in ra traceback lỗi `BrokenPipeError: [Errno 32] Broken pipe`.
- 🔍 **Nguyên nhân lỗi**: Trình duyệt đóng kết nối HTTP/SSE trước khi PyTorch hoàn tất ghi luồng dữ liệu xuống kết nối mạng socket.
- 🛠️ **Những gì đã sửa**: Bọc khối `try...except (BrokenPipeError, ConnectionResetError)` cho các hàm `_send_json`, `_send_file`, `_send_sse` tại [`demo-app/server.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/demo-app/server.py).
- ✅ **Kết quả thu được**: Server chạy ổn định tuyệt đối, không còn traceback rác trong terminal, phản hồi nút Đổi cấu hình ngay lập tức trong 0.01s.

---

### [2026-08-04] Entry #002 - Tối ưu Tốc độ Sinh từ (Live Token Streaming & Apple Metal MPS)
- ⏱️ **Thời gian**: 2026-08-04T13:30:00Z
- ❓ **Lý do sửa**: Người dùng phản hồi khi đổi sang mô hình Local SLM (Qwen2.5/SmolLM2) bị chờ lâu.
- 🔍 **Nguyên nhân lỗi**: Mô hình chạy CPU thuần và hệ thống cũ đợi sinh xong 100% toàn bộ câu trả lời rồi mới trả về một lượt.
- 🛠️ **Những gì đã sửa**:
  1. Bật tăng tốc `torch.backends.mps` (Metal GPU, `bfloat16`) trong [`bonerag/main_algo/generator.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/bonerag/main_algo/generator.py).
  2. Tích hợp `TextIteratorStreamer` để stream từng từ live qua SSE ngay millisecond sinh ra.
- ✅ **Kết quả thu me**: Tốc độ suy luận tăng 5-10x, chữ xuất hiện mượt mà từng từ trên giao diện web.

---

### [2026-08-04] Entry #001 - Chuẩn hóa tên Generator mặc định trên Topbar Web
- ⏱️ **Thời gian**: 2026-08-04T13:00:00Z
- ❓ **Lý do sửa**: Màn hình web hiển thị nhãn cũ `Gen: template`.
- 🔍 **Nguyên nhân lỗi**: Trình duyệt lưu `localStorage` key cũ mang tên `"template"`, trong khi backend đã đổi sang `local_context_synth`.
- 🛠️ **Những gì đã sửa**: Bổ sung hàm `_normalize_generator_name()` tại [`demo-app/server.py`](file:///Users/nghidothanh/Documents/School/TGMT/BoneRAG/demo-app/server.py) để tự động ánh xạ chuỗi `template` -> `local_context_synth`.
- ✅ **Kết quả thu được**: Màn hình web tự động cập nhật tên chuẩn `BoneRAG Evidence Synthesizer (0% Prior Leakage)`.
