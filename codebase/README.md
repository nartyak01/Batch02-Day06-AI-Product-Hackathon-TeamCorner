# Codebase

Đây là nơi nhóm nộp toàn bộ phần code của prototype. Mục tiêu là để giảng viên và các nhóm khác nhìn được sản phẩm chạy như thế nào, và mỗi thành viên đã đóng góp ra sao.

## Cấu trúc thư mục (skeleton)

```text
codebase/
├── database/
│   ├── facilities.csv
│   ├── specialties.csv   # description cho Gemini (không match keyword)
│   ├── doctors.csv     # 3 BS/khoa; availability_status: available | full
│   ├── slots.csv
│   ├── scripts/generate_vinmec_mock.py
│   └── bookings.csv      # lịch đã đặt — Nam append khi submit (PII)
├── src/
│   ├── tools/
│   │   ├── medical/   # Tool 1 — Đăng Khoa (2A202600922)
│   │   └── booking/   # Tool 2 — Hoàng Nam (2A202600870)
│   └── api/
│       └── main.py    # FastAPI (optional, cho UI/JS)
├── requirements.txt
└── README.md
```

### Chạy API medical tools (Python)

```powershell
cd codebase
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "."
uvicorn src.api.main:app --reload --port 8000
```

Thử nhanh: `GET http://127.0.0.1:8000/health`

**Tài liệu đầy đủ cho FE & Agent:** [docs/API-INTEGRATION.md](docs/API-INTEGRATION.md) (request/response, luồng, hàm Python, ví dụ fetch).

Swagger UI: `http://127.0.0.1:8000/docs`

## Nhóm cần làm

- Đưa mã nguồn của prototype vào folder này. Nếu prototype được deploy hoặc host ở nơi khác, hãy để lại đường link kèm hướng dẫn truy cập.
- Trong file `README.md` của nhóm, ghi rõ ba điều: cách chạy prototype (các bước cài đặt và biến môi trường nếu cần), những công cụ và API đã dùng (model AI, framework, công cụ dựng giao diện…), và phần phân công ai làm gì.
- Mỗi thành viên nên có ít nhất một commit thực chất trong repo — đây là căn cứ để ghi nhận đóng góp của từng người.

## Lưu ý

Đừng commit những thông tin nhạy cảm như API key hay file `.env`. Nếu prototype cần các biến môi trường, hãy dùng một file `.env.example` để mô tả các biến đó thay vì để lộ giá trị thật.
