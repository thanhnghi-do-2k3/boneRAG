# 🚀 Hướng dẫn Triển khai Tự động CI/CD (Deploy BoneRAG Miễn phí 100%)

Tài liệu này hướng dẫn cách đưa dự án **BoneRAG** lên môi trường Internet công khai với kiến trúc tách biệt (**Decoupled Frontend & Backend**), tự động cập nhật khi push code lên GitHub.

---

## 🏗️ Tổng quan Kiến trúc

* **Backend AI Engine:** Deploy trên **Hugging Face Spaces** (Docker SDK).
* **Frontend Web App:** Deploy trên **Vercel** (Vite + React).
* **Tự động hóa CI/CD:** Sử dụng **GitHub Actions** tự động đồng bộ code.

---

## 🛠️ Bước 1: Khởi tạo Hugging Face Space (Backend)

1. Truy cập [huggingface.co/new-space](https://huggingface.co/new-space).
2. Đặt tên Space: Ví dụ `boneRAG-backend`.
3. Chọn **SDK: Docker** -> Chọn **Blank / Plain Docker**.
4. Chọn tính năng **Public**.
5. Nhấn **Create Space**.

---

## 🔑 Bước 2: Thiết lập GitHub Secrets cho CI/CD

1. Truy cập **Hugging Face Token**: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) -> Tạo token mới với quyền **WRITE**.
2. Trên kho GitHub dự án của bạn (`https://github.com/thanhnghi-do-2k3/boneRAG`):
   * Vào **Settings** -> **Secrets and variables** -> **Actions**.
   * Nhấn **New repository secret**:
     * `HF_TOKEN`: dán token vừa tạo ở Hugging Face.
     * `HF_SPACE_NAME`: dán ID Space của bạn (Ví dụ: `thanhnghi-do-2k3/boneRAG-backend`).

👉 Từ bây giờ, mỗi khi bạn `git push` code lên GitHub, GitHub Action sẽ **tự động deploy backend sang Hugging Face**!

---

## 🌐 Bước 3: Deploy Frontend trên Vercel (Web UI)

1. Truy cập [vercel.com](https://vercel.com) và đăng nhập bằng tài khoản GitHub.
2. Nhấn **Add New Project** -> Chọn kho repo `boneRAG`.
3. Trong phần **Environment Variables**, thêm biến:
   * **Key:** `VITE_API_BASE_URL`
   * **Value:** `https://USERNAME-SPACE_NAME.hf.space` (Ví dụ: `https://thanhnghi-do-2k3-bonerag-backend.hf.space`).
4. Nhấn **Deploy**.

---

🎉 **Hoàn tất!** Bạn sẽ nhận được một đường link web chính thức (dạng `https://bonerag.vercel.app`) để truy cập từ bất kỳ đâu!
