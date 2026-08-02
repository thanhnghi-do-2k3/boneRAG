# BoneRAG algorithm

`code/bonerag/` chỉ chứa thuật toán cốt lõi và những thứ trực tiếp phục vụ việc triển khai paper.

```text
bonerag/
  main_algo/            Python package thuật toán
  tests/                Test cho pipeline
  evaluation/           Kết quả đánh giá từng cải tiến
  algorithm-logs/       Log thay đổi thuật toán
  implementation-plan/  Plan triển khai paper
```

Các phần không phải thuật toán đã nằm ngang hàng bên ngoài:

```text
code/
  bonerag/
  demo-app/
  research-server/
  papers/
```

## Test thuật toán

```bash
cd code/bonerag
python3 -m unittest discover -s tests
```

## Vai trò file chính

- `main_algo/data.py`: schema và knowledge base mẫu.
- `main_algo/encoder.py`: encoder baseline, sau này thay bằng encoder y sinh/vision-language thật.
- `main_algo/vector_index.py`: index cosine in-memory, sau này thay bằng FAISS.
- `main_algo/pipeline.py`: retrieve, gate, rerank, generate answer và streaming event.
- `evaluation/`: ghi kết quả thử nghiệm.
- `algorithm-logs/`: ghi thay đổi thuật toán và lý do.
