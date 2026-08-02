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
