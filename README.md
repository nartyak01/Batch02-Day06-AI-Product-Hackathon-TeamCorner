# Day06-C401-TeamCorner: VinmecCare AI Agent đặt lịch

Chào mừng đến với repository của nhóm! Dự án này là sản phẩm prototype được xây dựng trong kỳ Hackathon Day 06.

## Danh sách thành viên

- **Lê Đàm Quân** - 2A202600930 - Đảm nhiệm UI/UX
- **Nguyễn Tiến Đạt** - 2A202600595 - Đảm nhiệm Call API / Agent
- **Trần Nguyễn Đăng Khoa** - 2A202600922 - Đảm nhiệm Tool 1 (Medical routing tools)
- **Trần Hoàng Nam** - 2A202600870 - Đảm nhiệm Tool 2 (Booking/privacy tools)

## Mô tả ngắn sản phẩm

**VinmecCare AI Agent** là một trợ lý ảo hỗ trợ người bệnh (đặc biệt là những người lần đầu đặt lịch khám) có thể dễ dàng tìm kiếm chuyên khoa và khung giờ khám phù hợp chỉ thông qua việc mô tả triệu chứng trong màn hình chat.

Thay vì phải tự mò mẫm trên một biểu mẫu (form) phức tạp với nhiều lựa chọn y khoa khó hiểu, người dùng chỉ cần chat với AI. AI sử dụng Gemini 3.1 Flash Lite để:
- Phân tích triệu chứng (có thể hỏi thêm 1-2 câu để làm rõ nếu cần thiết).
- Gợi ý 2-3 chuyên khoa phù hợp cùng lý do giải thích.
- Cung cấp các khung giờ (slot) khám đang còn trống.
- Chuyển tiếp người dùng sang form đặt lịch đã được điền sẵn (pre-fill) thông tin chuyên khoa, cơ sở, thời gian và lý do khám. 

**Quyền riêng tư (Privacy-first):** Thông tin cá nhân (PII) như Họ tên, SĐT, Email, CCCD hoàn toàn không được gửi vào prompt của LLM. Người dùng chỉ nhập các thông tin này ở bước form cuối cùng, đảm bảo tính bảo mật và an toàn dữ liệu y tế.

## Cấu trúc Repository

```text
Day06-Lop-NhomXX/
├── README.md        ← Danh sách thành viên và mô tả ngắn sản phẩm
├── spec/            ← Chứa file SPEC sản phẩm (spec.md) và các tài liệu liên quan
└── codebase/        ← Toàn bộ source code prototype (Frontend Next.js & Backend FastAPI)
```

## Chạy dự án (Prototype)

Prototype bao gồm Frontend (Next.js) và Backend (FastAPI).

### 1. Backend (FastAPI)
Môi trường yêu cầu: Python 3.x
```powershell
cd codebase
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "."
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```
- Backend chạy tại: `http://127.0.0.1:8000` 
- API Docs (Swagger UI): `http://127.0.0.1:8000/docs`
- *Lưu ý: Bạn cần tạo file `.env` trong thư mục `codebase/` (sao chép từ `.env.example`) và điền `GEMINI_API_KEY`.*

### 2. Frontend (Next.js)
Môi trường yêu cầu: Node.js
```bash
cd codebase/frontend
npm install
npm run dev
```
- Giao diện người dùng chạy tại: `http://127.0.0.1:3000`
- *Lưu ý: Cần có file `.env` trong thư mục `codebase/frontend/` (sao chép từ `.env.example`) để trỏ biến `BACKEND_API_URL` tới backend.*

---
*Dự án thuộc Batch 02 · Ngày 06 — VinUni A20 · AI Thực Chiến · 2026*
