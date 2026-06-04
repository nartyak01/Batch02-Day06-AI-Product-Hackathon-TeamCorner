# Codebase

Repo hiện chia 3 phần chính:

- `frontend/`: Next.js UI + API route nội bộ cho demo nhanh.
- `src/`: FastAPI backend/tool layer từ phần của Khoa, dùng cho agent và form integration.
- `data/`: CSV canonical dùng chung cho cả frontend và backend.

## Chạy frontend

```bash
cd frontend
npm install
npm run dev
```

Mở `http://127.0.0.1:3000`.

Frontend gọi backend qua `frontend/.env.example`:

```env
BACKEND_API_URL=http://127.0.0.1:8000
```

## Chạy backend Python

```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI: `http://127.0.0.1:8000/docs`.

Backend agent dùng biến ở root `.env.example`:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
```

## Data

Không tạo thêm DB riêng. Tất cả database nằm trong `data/`:

- `facilities.csv`
- `specialties.csv`
- `doctors.csv`
- `slots.csv`
- `bookings.csv`
