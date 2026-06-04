# Thin SPEC — VinmecCare · AI Agent đặt lịch (symptom → khoa/slot → form)

Thin SPEC không phải PRD đầy đủ. Đây là bản cam kết đủ rõ để sáng Day 06 nhóm build ngay.

## 1. Track, product/app và user

**Track:** Healthcare  
**Product/app thật (tham chiếu):** Trợ lý ảo VinmecCare + form [Đăng ký khám](http://vinmec.com/vie/dang-ky-kham/)  
**Prototype Day 06:** Chatbot **AI agent** (mock Vinmec) — không tích hợp VinBigdata production  
**LLM dùng cho prototype:** Gemini 3.1 Flash Lite

**User cụ thể:** Người bệnh lần đầu mô tả triệu chứng bằng tiếng Việt, không rành chọn khoa/bác sĩ  
**Nhóm có phải user thật không?** Đã self-use VinmecCare; prototype giả lập flow tốt hơn as-is thật  

## 2. Evidence summary

| Evidence | Nguồn | User/pain nói lên điều gì? | SPEC phải đổi gì? |
|---|---|---|---|
| Chat: đau bụng muốn hẹn lịch → bot hỏi tuổi/cơ sở → link + hotline, không gợi ý khoa | Screenshot self-use | Cần agent map symptom → khoa/bác sĩ/slot | LLM + mock catalog + slot tool |
| Chatbot Vinmec vẫn yêu cầu điền form / gọi tư vấn viên thủ công | Research evidence nhóm | Handoff chưa giải quyết việc đặt lịch ngay trong luồng chat | Agent phải gọi tool lấy khoa + lịch trống, rồi mở form có context |
| Form web nhiều field, user tự chọn | vinmec.com/vie/dang-ky-kham/ | Ma sát cao, dễ bỏ giữa chừng | Pre-fill phần đặt lịch (không PII) |
| Handoff mất context | Chat Vinmec thật | Cần chuyển state sang form | Object `bookingDraft` từ agent → form |
| User có thể nhập SĐT/email/CCCD ngay trong chat | Risk analysis nhóm | Nếu PII bay vào LLM/transcript thì sai privacy boundary | Chặn regex ở frontend + system prompt bỏ qua PII |

## 3. Pain statement

```text
User mô tả triệu chứng và muốn đặt lịch qua chat,
gặp khó vì bot thật chủ yếu gửi link/form và bắt user tự chọn khoa/bác sĩ.
Điều này khiến user phải tự mày mò, dễ bỏ giữa chừng, chọn sai,
hoặc phải gọi hotline để được tư vấn thủ công.
Khi số lượng user tăng, gánh nặng lại dồn sang tư vấn viên;
chatbot vì vậy không tạo tác dụng lớn ngoài việc điều hướng user sang form.
Bằng chứng: screenshot VinmecCare + form đăng ký khám.
```

## 4. Build slice

```text
Cho người bệnh lần đầu đang nhập triệu chứng trong chat Vinmec mock,
prototype dùng Gemini 3.1 Flash Lite + tool/mock DB để hỏi thêm triệu chứng,
gợi ý khoa nên khám, lấy lịch trống theo khoa/cơ sở,
cho user chọn slot hoặc tự override khoa,
rồi mở form đặt lịch đã giữ context trong session hiện tại.
User chỉ nhập PII trong form riêng; form submit thẳng tới mock storage demo,
trả `ticketId` và có tab xem lại các lịch đã đặt.
Nếu user không ưng khoa AI gợi ý, form vẫn cho đổi chuyên khoa trước khi submit;
slot/bác sĩ mock sẽ refresh theo khoa mới.
Trong tab này, user có thể bấm "Edit thông tin" để sửa thông tin cá nhân
hoặc thông tin liên hệ mà không đưa dữ liệu đó quay lại LLM.
Prototype xử lý failure mode bằng low-confidence, `Pending_Doctor_Review`,
hotline/tư vấn viên gọi lại, regex chặn PII ở chat, và system prompt bỏ qua PII.
```

### Luồng sản phẩm

| Giai đoạn | Agent/UI phải làm gì? | Output |
|---|---|---|
| 1 — Lấy triệu chứng hiện tại | User nhập triệu chứng. AI hỏi thêm tối đa 2 câu về thời điểm, mức độ, vị trí đau, triệu chứng đi kèm. | `symptomSummary`, `confidence`, `redFlagRisk` |
| 2 — Gọi tool | AI gọi `suggestSpecialty(symptomSummary)` và `getAvailableSlots(specialty, facility?)`. UI hiển thị khoa + lý do ngắn + slot trống để user chọn. | `bookingDraft` có khoa, cơ sở, slot, lý do khám |
| 3 — Fallbacks | Nếu user override khoa, AI nhượng bộ và có thể đánh dấu `Pending_Doctor_Review`; nếu triệu chứng quá rối/hoang mang hoặc có red flag, chuyển hotline/callback. | `bookingDraft` hoặc `callbackDraft` |
| 4 — Form/session | Khi chốt A/B/C, frontend gọi `renderBookingForm(draft)`. Form cho sửa chuyên khoa/slot trước submit; nếu đổi khoa thì refresh slot/bác sĩ mock. | `ticketId`, tab "Lịch đã đặt" |
| 5 — Review/edit booking | Tab "Lịch đã đặt" hiển thị ticket đã submit. User bấm "Edit thông tin" để sửa PII/contact trên form riêng. | ticket đã cập nhật, không gọi LLM |

### Kiến trúc prototype (ranh giới dữ liệu)

```text
┌─────────────────────────────────────────────────────────────┐
│  TẦNG 2 — Client-side PII interception                      │
│  Regex chặn trước khi gửi chat: SĐT/email/CCCD.             │
│  Nếu phát hiện PII: disable nút Gửi + pop-up yêu cầu xóa.   │
└──────────────────────────┬──────────────────────────────────┘
                           │ chỉ gửi symptom text đã qua guard
┌──────────────────────────▼──────────────────────────────────┐
│  TẦNG 4 — System prompt safeguard                           │
│  LLM bỏ qua PII nếu user cố nhập; không nhắc lại PII;       │
│  nhắc user nhập thông tin cá nhân ở form bảo mật riêng.     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  PHASE A — Chat intake (Gemini 3.1 Flash Lite)              │
│  Input: triệu chứng, tuổi/năm sinh, cơ sở/khu vực, no PII.  │
│  Output: symptomSummary, confidence, redFlagRisk.           │
└──────────────────────────┬──────────────────────────────────┘
                           │ tool calls
┌──────────────────────────▼──────────────────────────────────┐
│  PHASE B — Tool/mock DB                                     │
│  suggestSpecialty(), getAvailableSlots(), createDraft().    │
│  Output: bookingDraft / callbackDraft / pendingReviewDraft. │
└──────────────────────────┬──────────────────────────────────┘
                           │ handoff JSON/state, không qua prompt
┌──────────────────────────▼──────────────────────────────────┐
│  PHASE C — Form đặt lịch (KHÔNG LLM)                        │
│  Pre-filled: cơ sở, khoa, thời gian, lý do, trạng thái.     │
│  Editable trước submit: khoa, slot, thông tin người dùng.    │
│  User nhập: họ tên, SĐT, ngày sinh, giới tính, email.       │
│  Save session + submit mock storage → ticketId + tab lịch    │
│  đã đặt; tab có nút Edit thông tin cho từng ticket.          │
└─────────────────────────────────────────────────────────────┘
```

**Nguyên tắc privacy:** Họ tên, SĐT, email, CMND… **không** gửi vào prompt LLM; không log PII trong transcript agent. Chỉ `bookingDraft` + field form Phase C.

### Regex chặn PII ở frontend

| Loại PII | Pattern demo | Action |
|---|---|---|
| SĐT Việt Nam | `/(?:\+?84|0)(?:\d[\s.-]?){9}\b/` hoặc 10 chữ số liên tiếp | Disable nút "Gửi"; pop-up yêu cầu xóa SĐT khỏi tin nhắn |
| Email | `/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i` | Disable nút "Gửi"; pop-up yêu cầu xóa email |
| CCCD/CMND | `/\b\d{9}\b|\b\d{12}\b/` | Disable nút "Gửi"; pop-up yêu cầu xóa CCCD/CMND |

Microcopy pop-up:

```text
Phát hiện thông tin cá nhân (SĐT/Email/CCCD). Vui lòng xóa thông tin này khỏi tin nhắn.
AI chỉ cần biết triệu chứng bệnh của bạn. Bạn sẽ nhập thông tin cá nhân ở form đặt lịch riêng.
```

Tên người dùng khó chặn chính xác bằng regex nên không dùng regex tên trong chat. UI dùng warning dưới input + system prompt: không yêu cầu tên/mã thành viên trong hội thoại, chỉ nhập ở form sau khi chốt lịch.

### System prompt safeguard

```text
Bạn là AI booking agent cho Vinmec mock. Trong chat, chỉ thu thập triệu chứng,
tuổi/năm sinh, khu vực/cơ sở mong muốn và thời gian khám mong muốn.
Không yêu cầu hoặc lưu họ tên, số điện thoại, email, CCCD/CMND, mã thành viên.
Nếu user chủ động cung cấp PII, hãy bỏ qua hoàn toàn thông tin đó,
không nhắc lại trong câu trả lời, và nói:
"Để bảo mật, tôi không lưu trữ thông tin cá nhân của bạn. Vui lòng chỉ mô tả triệu chứng;
thông tin cá nhân sẽ được nhập ở form đặt lịch riêng."
```

### Mock data (Day 06)

| Dataset | Nội dung tối thiểu |
|---------|-------------------|
| `facilities` | 2–3 cơ sở HN (Times City, Smart City…) |
| `specialties` | 5–8 khoa (Tiêu hóa, Nội tổng quát, Cấp cứu flag…) |
| `doctors` | 2–3 BS / khoa (optional chọn) |
| `slots` | 3 ngày gợi ý (giống UI Vinmec) |
| `redFlags` | Rule/keyword → chặn gợi ý khoa, show hotline |
| `bookings` | Lưu mock ticket đã đặt (`ticketId`, khoa, slot, trạng thái, thông tin form) cho tab lịch đã đặt |

**Lưu booking demo:** Khi user submit form, prototype có thể lưu vào CSV hoặc local state để demo tab "Lịch đã đặt". Nút "Edit thông tin" chỉ sửa thông tin người dùng/contact trên form, không gọi lại LLM. CSV/local state chỉ dùng dữ liệu giả cho demo.

### AI decision (một việc cụ thể)

Map **triệu chứng + tuổi + cơ sở** → rank **2–3 chuyên khoa** (có `reason` ngắn); user **chọn hoặc override** khoa trong chat/form → agent lấy slot từ mock. Nếu override có dấu hiệu sai/rủi ro, set status `Pending_Doctor_Review` để bác sĩ triage xem lại lịch sử chat ẩn danh và tự chốt khoa trên màn hình nội bộ mock.

## 5. Auto/Aug decision

- [x] **Augmentation:** AI gợi ý khoa/BS/slot; user quyết và sửa trên form.
- [x] **Conditional automation (một phần):** Agent tự điền form Phase C từ `bookingDraft`; Phase C submit không qua LLM.
- [ ] **Automation:** Không — không auto-submit đặt lịch; không auto-điền PII.

**Lý do:** Rủi ro y tế + privacy; PII tách khỏi LLM là requirement prototype.  
**Human role:** decider (chọn khoa/BS) + nhập PII trên form + rescuer (red flag → hotline)  

## 6. Four paths

| Path | Prototype phải thể hiện gì? |
|---|---|
| A — Happy path | AI nói: "Dựa trên triệu chứng, bạn nên khám Khoa Tim Mạch. Hiện có lịch trống lúc 14:00 chiều nay." User đồng ý → mở form pre-fill → user nhập PII → submit mock → ticket ID |
| B — User/Doctor override | User nói trong chat hoặc đổi trên form: "Không, tôi muốn khám Tiêu Hóa cơ." AI/UI nhượng bộ, refresh slot theo Khoa Tiêu Hóa. Nếu nghi ngờ, set `Pending_Doctor_Review` và lưu lịch sử chat ẩn danh để bác sĩ triage xem lại |
| C — Escalation | Triệu chứng quá lung tung/hoang mang hoặc có red flag → không ép chọn khoa; hiện hotline hoặc form callback để tư vấn viên gọi sớm nhất → ticket ID dạng `CALLBACK-*` |
| PII correction | User nhập SĐT/email/CCCD trong chat → frontend chặn regex trước server/LLM; nếu lọt qua, system prompt bỏ qua và nhắc nhập ở form riêng |

## 7. Failure mode nguy hiểm nhất

```text
Nếu user mô tả triệu chứng nặng (red flag),
AI có thể gợi ý nhầm khoa ngoại trú,
hậu quả là trễ điều trị.
Prototype: rule red-flag trước LLM → chặn bookingDraft → cảnh báo + hotline;
không chuyển sang form đặt lịch thường, chỉ mở callback form nếu user muốn tư vấn viên gọi lại.
Owner test: Trần Nguyễn Đăng Khoa (2A202600922).
```

**Failure privacy:** Nếu user paste SĐT/email/CCCD vào chat → frontend regex chặn trước server/LLM. Nếu thông tin vẫn lọt qua bằng cách viết lách, system prompt yêu cầu LLM bỏ qua, không nhắc lại, không lưu vào `bookingDraft`; PII chỉ được nhập trong form.

## 8. Owner plan cho sáng Day 06

| Thành viên | Việc phụ trách | Deliverable |
|---|---|---|
| Lê Đàm Quân (2A202600930) | Research evidence + demo narrative | Evidence pack + script demo |
| Nguyễn Tiến Đạt (2A202600595) | Chat UI + agent flow Gemini | Phase A intake + response states |
| Trần Nguyễn Đăng Khoa (2A202600922) | SPEC + mock JSON + red-flag rules | Mock khoa/cơ sở/slot + triage rules |
| Trần Hoàng Nam (2A202600870) | Form/session mock + PII guard | Regex guard, `renderBookingForm`, ticket ID, tab lịch đã đặt, edit thông tin |

### Demo script (3 phút)

1. Nhập triệu chứng (không nhập họ tên/SĐT trong chat).
2. Agent hỏi thêm 1–2 câu, gợi ý khoa + slot trống.
3. Chọn happy path hoặc override khoa → form mở với draft đã có khoa/slot/trạng thái; có thể đổi chuyên khoa ngay trên form nếu không ưng.
4. Điền PII trên form → submit → nhận ticket ID → lưu mock booking.
5. Mở tab "Lịch đã đặt" → bấm "Edit thông tin" → sửa SĐT/email → lưu lại ticket.
6. Thử PII trong chat để thấy regex chặn; thử red flag để thấy hotline/callback.
