# BoneRAG implementation workspace

`code/` được tổ chức để có thể tách riêng phần triển khai paper.

```text
code/
  bonerag/              Thuật toán cốt lõi + plan/evaluation/log thuật toán
  demo-app/             Frontend demo + server demo
  research-server/      Web report nghiên cứu
  papers/               Paper gốc/bổ sung/project paper
```

## Chạy demo

```bash
cd code/demo-app/frontend
npm install
npm run build

cd ../../..
python3 code/demo-app/server.py --port 8088
```

## Test thuật toán

```bash
cd code/bonerag
python3 -m unittest discover -s tests
```
