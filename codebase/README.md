# Codebase

Repo hiện chia 3 phần chính:

- `frontend/`: Next.js UI + API route nội bộ cho demo nhanh.
- `src/`: FastAPI backend/tool layer (medical + booking + agent).
- `data/`: CSV canonical dùng chung cho cả frontend và backend.

## Cấu trúc thư mục

```text
codebase/
├── data/
│   ├── facilities.csv
│   ├── specialties.csv   # description cho Gemini (không match keyword)
│   ├── doctors.csv       # availability_status: available | full
│   ├── slots.csv
│   └── bookings.csv      # PII — append khi submit
├── src/
│   ├── tools/
│   │   ├── medical/   # Tool 1 — Đăng Khoa (2A202600922)
│   │   └── booking/   # Tool 2 — Hoàng Nam (2A202600870)
│   ├── vinmec_agent/
│   └── api/
│       └── main.py
├── frontend/
├── scripts/generate_vinmec_data.py
├── requirements.txt
└── docs/API-INTEGRATION.md
```

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

```powershell
cd codebase
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "."
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

Thử nhanh: `GET http://127.0.0.1:8000/health`

**Tài liệu đầy đủ cho FE & Agent:** [docs/API-INTEGRATION.md](docs/API-INTEGRATION.md)

OpenAPI: `http://127.0.0.1:8000/docs`

Backend agent dùng biến ở `.env.example`:

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

**Regenerate CSV:** `python scripts/generate_vinmec_data.py`
