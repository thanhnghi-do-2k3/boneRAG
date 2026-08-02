# BoneRAG Research Hub

Mini web report cho hướng nghiên cứu BoneRAG: VQA bệnh lý xương sử dụng Image RAG.

## Chạy local

```bash
cd research
npm install
npm run dev
```

Sau đó mở URL Vite in ra trong terminal.

## Build

```bash
cd research
npm run build
```

## Thêm nghiên cứu mới

Mở `src/research-data.js`, thêm object vào mảng `papers`.

Các nhóm hiện có:

- `medical-rag`: RAG đa phương thức y khoa.
- `visual-rag`: Visual/Image RAG tổng quát.
- `bone`: dataset/model ảnh xương.
- `region`: region retrieval, utility selection, graph RAG.

Nên giữ mỗi paper theo cùng khung:

- `method`: tác giả đã làm gì.
- `result`: kết quả chính.
- `philosophy`: triết lý/cơ chế đằng sau.
- `gap`: thiếu sót.
- `use`: BoneRAG học được gì.
