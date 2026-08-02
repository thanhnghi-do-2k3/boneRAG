# Demo app

Thư mục này chứa phần demo, không chứa thuật toán lõi.

```text
demo-app/
  server.py
  frontend/
  web/
```

Demo server import pipeline từ `../bonerag/main_algo`.

## Chạy

```bash
cd code/demo-app/frontend
npm install
npm run build

cd ../../..
python3 code/demo-app/server.py --port 8088
```
