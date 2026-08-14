# Evaluation workspace

Thư mục này dùng để đánh giá từng cải tiến của BoneRAG một cách có cấu trúc.

## Khi nào thêm một dòng đánh giá?

Mỗi lần thay một thành phần quan trọng, hãy tạo một dòng mới trong `experiments.jsonl`:

- encoder: ví dụ thay hashing bằng BiomedCLIP hoặc BGE-VL
- index: ví dụ thay in-memory cosine bằng FAISS
- retrieval: ví dụ thêm ROI, body-part filter, hard negative
- reranker: ví dụ thêm cross-encoder hoặc factual reranker
- generator: ví dụ thay template bằng MLLM thật
- guardrail: ví dụ thêm cơ chế từ chối khi evidence yếu

## Metric tối thiểu

- `retrieval_recall_at_k`: evidence đúng có nằm trong top-k không
- `answer_accuracy`: câu trả lời đúng nhãn bệnh không
- `faithfulness`: câu trả lời có bám evidence không
- `latency_ms`: tổng thời gian pipeline
- `notes`: lỗi thường gặp và quyết định giữ/bỏ cải tiến

## Format

Mỗi dòng trong `experiments.jsonl` là một JSON độc lập để dễ append, dễ đọc bằng Python/Pandas.

## Paper-ready artifact sau benchmark

Sau mỗi run benchmark, backend/CLI sinh thêm `paper_evaluation` trong run JSON.
Artifact này không tạo baseline giả; nó chỉ phân tích các system đã chạy thật
trên cùng case IDs.

Benchmark hiện tại là **FracAtlas-derived closed grounded VQA pilot**:

- FracAtlas không phải native VQA dataset; câu hỏi yes/no được sinh từ annotation.
- BTXRD/BTRXD và GRAZPEDWRI-DX được track trong `grounded_vqa_manifest` nhưng
  chưa chạy cho đến khi có loader riêng.
- RadBench/ImageCLEF VQA-Med musculoskeletal subset là external native-VQA
  benchmark dự kiến, không được tính là kết quả hiện tại.
- Grounding bằng IoU/Dice/mAP chỉ được claim sau khi hệ thống output box/mask
  trên query image.

Matrix mặc định hiện so BoneRAG với nhiều thuật toán cùng bài toán:

- Image-only nearest-neighbor RAG
- zero-shot prompt classifier
- kNN majority vote classifier
- similarity-weighted kNN classifier
- class-centroid/prototype classifier
- BoneRAG

Nội dung chính:

- benchmark scope: active dataset, native-VQA status, dataset roadmap, blocked claims
- confidence interval 95% cho metric hệ thống
- paired BoneRAG-vs-every-executed-baseline delta theo từng ảnh
- exact McNemar/binomial test cho metric nhị phân
- decision/retrieval/answer error breakdown TP/TN/FP/FN/unknown
- sanity/discrimination audit: cảnh báo nếu nhiều system ra cùng prediction,
  cùng top evidence, hoặc một metric có cùng giá trị cho toàn bộ matrix
- claim guidance: được viết gì, nên cảnh báo gì, và claim nào bị chặn

CLI:

```bash
python3 -m bonerag.evaluation.run_benchmark \
  --encoder biomedclip --generator synth --cases 128 --paper-report
```

Xuất file Markdown/CSV/SVG:

```bash
python3 -m bonerag.evaluation.run_benchmark \
  --encoder biomedclip --generator synth --cases 128 \
  --export-paper-dir /content/drive/MyDrive/BoneRAG_Data/paper_reports
```
