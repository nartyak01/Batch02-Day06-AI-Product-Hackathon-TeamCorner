# Codebase

Đây là nơi nhóm nộp toàn bộ phần code của prototype. Mục tiêu là để giảng viên và các nhóm khác nhìn được sản phẩm chạy như thế nào, và mỗi thành viên đã đóng góp ra sao.

## Agent core

Code đã được tách theo hướng clean architecture:

```text
codebase/
├── main.py                         # CLI JSON adapter cho Next.js child_process
├── streamlit_app.py                # UI test tạm để chạy agent trước khi ghép Next.js
└── vinmec_agent/
    ├── application/                # BookingAgent, prompt, ports
    ├── domain/                     # state constants, PII guard, response contract, text utils
    └── infrastructure/             # Gemini adapter, mock tools, mock data
```

`main.py` chỉ là entrypoint mỏng. Logic chính nằm trong `vinmec_agent/application/agent_service.py`.

Agent hiện có:

- ReAct-style flow: intake triệu chứng -> kiểm tra red flag/PII -> Gemini -> mock tools -> `booking_draft`.
- System prompt bảo vệ privacy: không hỏi/lưu/nhắc lại họ tên, SĐT, email, CCCD.
- Fallback rule-based nếu thiếu API key, Gemini lỗi, quota lỗi hoặc SDK chưa cài.
- CLI JSON adapter để Next.js gọi bằng `child_process`, không cần tách backend API.
- Mock tools/database tạm: facilities, specialties, doctors, slots, red flags, booking draft.

### Cài dependency

```bash
pip install -r requirements.txt
```

### Chạy Streamlit test UI

```bash
streamlit run streamlit_app.py
```

Streamlit chỉ là test harness để tự bấm flow trước khi ghép UI/UX Next.js. UI cuối có thể bỏ file này và gọi `main.py`.

### Chạy thử CLI nhanh

```bash
python main.py "Tôi bị đau bụng âm ỉ từ hôm qua, muốn khám ở Vinmec Hà Nội"
```

Hoặc truyền JSON qua stdin, đúng kiểu Next.js nên gọi:

```bash
echo '{"user_message":"Tôi bị đau bụng âm ỉ từ hôm qua, muốn khám ở Vinmec Hà Nội","history":[],"context":{}}' | python main.py
```

Output luôn là JSON:

```json
{
  "reply": "...",
  "state": "suggesting_slots",
  "symptom_summary": "...",
  "confidence": 0.62,
  "red_flag_risk": false,
  "suggested_specialties": [],
  "slots": [],
  "booking_draft": {},
  "callback_draft": null,
  "needs_more_info": false,
  "questions": [],
  "meta": {}
}
```

### Biến môi trường

Copy `.env.example` thành `.env` trong thư mục `codebase/` nếu muốn gọi Gemini thật:

```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.1-flash-lite
AGENT_DEBUG=0
```

Nếu không có `GEMINI_API_KEY`, agent vẫn chạy bằng fallback rules để demo không bị crash.

### Gợi ý Next.js bridge

Next.js có thể gọi agent bằng child process:

```ts
import { spawn } from "node:child_process";

export function runAgent(payload: unknown): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn("python", ["codebase/main.py"]);
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => (stdout += chunk.toString()));
    child.stderr.on("data", (chunk) => (stderr += chunk.toString()));
    child.on("close", (code) => {
      if (code !== 0) return reject(new Error(stderr || `agent exited ${code}`));
      resolve(JSON.parse(stdout));
    });

    child.stdin.write(JSON.stringify(payload));
    child.stdin.end();
  });
}
```

## Nhóm cần làm

- Đưa mã nguồn của prototype vào folder này. Nếu prototype được deploy hoặc host ở nơi khác, hãy để lại đường link kèm hướng dẫn truy cập.
- Trong file `README.md` của nhóm, ghi rõ ba điều: cách chạy prototype (các bước cài đặt và biến môi trường nếu cần), những công cụ và API đã dùng (model AI, framework, công cụ dựng giao diện…), và phần phân công ai làm gì.
- Mỗi thành viên nên có ít nhất một commit thực chất trong repo — đây là căn cứ để ghi nhận đóng góp của từng người.

## Lưu ý

Đừng commit những thông tin nhạy cảm như API key hay file `.env`. Nếu prototype cần các biến môi trường, hãy dùng một file `.env.example` để mô tả các biến đó thay vì để lộ giá trị thật.
