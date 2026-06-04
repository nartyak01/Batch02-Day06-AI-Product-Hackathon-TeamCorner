# Toolkit — Từ Evidence Đến Build Slice

Dùng sau khi nhóm đã có evidence. Mục tiêu là chốt một build slice đủ nhỏ cho Day 06.

## 1. Gom evidence thành cụm

Gom theo **workflow/pain**, không gom theo tên feature.

Ví dụ cụm tốt:

- "Không biết chọn chuyên khoa"
- "Không hiểu vì sao bị tính phí"
- "Muốn sửa output nhưng không có chỗ sửa"
- "Bot trả lời tự tin nhưng không dẫn nguồn"

## 2. Viết insight

Form:

```text
User [segment] không chỉ cần [surface need].
Họ thật ra cần [deeper need],
vì [evidence pattern].
```

Ví dụ:

```text
Người lần đầu đi khám không chỉ cần danh sách chuyên khoa.
Họ cần hỗ trợ ra quyết định an toàn,
vì nhiều review/observation cho thấy họ không biết triệu chứng của mình nên đi khoa nào.
```

## 3. Viết opportunity

Form:

```text
Cơ hội là dùng AI để [augment/automate hành động hẹp],
giúp user [kết quả],
trong khi vẫn kiểm soát [failure/risk].
```

## 4. Chọn build slice

Build slice tốt phải qua 5 câu hỏi:

| Câu hỏi | Đạt khi |
|---|---|
| User cụ thể chưa? | Nói được ai dùng, trong bối cảnh nào. |
| Task đủ hẹp chưa? | Demo được trong 3-5 phút. |
| AI decision rõ chưa? | AI gợi ý/tự làm một việc cụ thể. |
| Failure path rõ chưa? | Có một case AI không chắc hoặc sai để test. |
| Có evidence không? | Có bằng chứng từ self-use/review/user/competitor. |

## 5. Quyết định: giữ, giảm scope, hay đổi hướng?

| Tình huống | Quyết định |
|---|---|
| Evidence yếu, user mơ hồ | Dừng build sâu; quay lại research 20 phút. |
| Ý tưởng quá rộng | Giữ domain, cắt xuống một flow. |
| AI không cần thiết | Dùng rule/manual prototype; ghi rõ vì sao không dùng AI sâu. |
| Rủi ro cao | Chọn augmentation hoặc conditional automation. |
| Không demo được trong 1 ngày | Đưa phần lớn vào backlog, giữ một path nhỏ. |

## 6. Câu chốt cuối

Điền câu này trước khi rời lớp:

```text
Dựa trên [evidence],
nhóm sẽ build [prototype slice],
cho [user],
để giải quyết [pain],
bằng cách AI [augment/automate task],
và sẽ test failure path [failure mode].
```

## 7. Backlog

Những thứ **không build trong Day 06**:

- API đặt lịch Vinmec thật + OTP production
- VinBigdata / chat production
- Lưu PII vào vector DB / fine-tune từ transcript
- Đa ngôn ngữ, bảo hiểm, thanh toán

---

## Kết quả nhóm Team Corner — Vinmec (đã chốt — cập nhật)

### Cụm evidence

- Symptom không map được khoa/BS trong chat thật
- Handoff link — user điền lại form từ đầu
- Form Vinmec tách field đặt lịch vs thông tin khách hàng → mô hình 2 phase phù hợp
- Chatbot hiện vẫn đẩy user sang form/gọi tư vấn viên thủ công
- User có thể nhập PII vào chat nếu không có guard chủ động

### Insight

```text
User cần agent đặt lịch từ triệu chứng, không chỉ link.
Họ cần form gần hoàn tất sau chat và không muốn đưa SĐT/email/CCCD/họ tên vào LLM,
vì chat thật không nối symptom → booking, form thật đã tách PII,
và luồng hiện tại vẫn phụ thuộc vào form/call tư vấn thủ công.
```

### Opportunity

```text
AI agent trong chat: Gemini 3.1 Flash Lite + mock tools
(cơ sở, khoa, bác sĩ, slot) từ triệu chứng + tuổi + khu vực.
Handoff bookingDraft/callbackDraft → form pre-fill (không LLM), chuyên khoa/slot vẫn editable trước submit.
User chỉ nhập PII trên form và submit vào mock storage — dữ liệu cá nhân không qua prompt.
Tab "Lịch đã đặt" cho xem lại ticket và edit thông tin người dùng ngoài LLM.
Frontend regex chặn SĐT/email/CCCD trước khi tin nhắn bay lên server/LLM.
```

### Build slice — checklist

| Câu hỏi | Đạt? |
|---|---|
| User cụ thể? | Có — lần đầu đặt khám, mô tả triệu chứng |
| Task hẹp? | Có — agent + pre-fill + PII form (mock, 1 ngày) |
| AI decision rõ? | Có — map symptom → 2–3 khoa; user chọn/đổi khoa; lấy BS/slot từ mock |
| Failure path? | Có — happy path, user override khoa trong chat/form, escalation hotline/callback, PII trong chat bị chặn |
| Evidence? | Có screenshot Vinmec + form web |

### Quyết định scope

**Giữ** pain Vinmec · **Mở rộng có kiểm soát:** chat agent + form (vẫn mock) · **Augmentation + privacy:** LLM không nhận PII · **Submit** ngoài LLM · **Ticket/session:** lưu lịch đã đặt trong mock storage, có edit thông tin người dùng.

### Kiến trúc 2 phase (tóm tắt)

| Phase | Có LLM? | Dữ liệu |
|-------|---------|---------|
| Tầng 2 — Frontend guard | Không | Regex chặn SĐT/email/CCCD trước server/LLM |
| Tầng 4 — System prompt | Có | Bỏ qua PII nếu user cố nhập; không nhắc lại |
| A — Chat agent | Có | Triệu chứng, tuổi, cơ sở; mock khoa/BS/slot |
| B — Form đặt lịch/callback | **Không** | Pre-fill từ `bookingDraft`; user có thể đổi khoa/slot, nhập PII, submit mock, nhận ticket ID; tab lịch đã đặt có edit thông tin |

### Câu chốt cuối

```text
Dựa trên evidence VinmecCare + form đăng ký khám,
nhóm sẽ build chatbot AI agent dùng Gemini 3.1 Flash Lite
(symptom → hỏi thêm → gợi ý khoa/BS/slot từ mock tools),
handoff sang form đã fill thông tin đặt lịch/callback,
user có thể đổi chuyên khoa/slot nếu không ưng rồi điền thông tin cá nhân và submit không qua LLM,
nhận ticket ID, xem lại và edit thông tin ở tab lịch đã đặt,
và test happy path + override khoa + escalation + regex chặn PII trong chat.
```
