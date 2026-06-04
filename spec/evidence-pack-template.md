# Evidence Pack — Team Corner · VinmecCare

Nộp kèm thin SPEC cuối Day 05.

## 1. Nhóm và track

**Tên nhóm:** Team Corner (Batch02-Day05-AI-Product-Labs-TeamCorner)  
**Track:** Healthcare — bệnh viện / đặt lịch khám  
**Product/app đã chọn (tham chiếu):** Trợ lý ảo VinmecCare (Vinmec, VinBigdata)  
**LLM dùng cho prototype:** Gemini 3.1 Flash Lite
**Build slice Day 06 (đã chốt):** Chatbot **AI agent** — triệu chứng + input không PII → LLM + **mock** (khoa, bác sĩ, cơ sở, slot) → user chọn slot / override khoa trong chat hoặc form → **form pre-fill** (đặt lịch hoặc callback) → user chỉ nhập **thông tin cá nhân** → submit **không qua LLM** → trả ticket ID + tab lịch đã đặt có edit thông tin

| Thành viên | Mã thành viên |
|---|---|
| Lê Đàm Quân | 2A202600930 |
| Nguyễn Tiến Đạt | 2A202600595 |
| Trần Nguyễn Đăng Khoa | 2A202600922 |
| Trần Hoàng Nam | 2A202600870 |

## 2. Self-use evidence

| Observation | Screenshot/link | Path liên quan | Điều học được |
|---|---|---|---|
| User mô tả đau bụng/mắc ỉa và muốn hẹn lịch; bot chỉ hỏi tuổi/năm sinh | `assets/vinmec-chat-01-trien-chung.png` | Intake | Cần agent hỏi thêm triệu chứng có cấu trúc, không dừng ở tuổi |
| User trả lời "2004"; bot hỏi cơ sở bệnh viện bằng free text | `assets/vinmec-chat-02-tuoi-co-so.png` | Low-confidence / routing | Mock facilities + chips thay free text |
| User chọn Vinmec ở Hà Nội; bot gửi link đặt khám và danh sách hotline | `assets/vinmec-chat-03-link-hotline.png` | Failure / handoff | Thay link/hotline bằng form pre-fill + slot trống trong prototype |
| Chatbot vẫn yêu cầu người dùng điền form/gọi tư vấn viên thủ công | Research evidence nhóm | Handoff / abandonment | Agent phải gọi tool lấy lịch trống, rồi mở form có session context |
| Form web: cơ sở, khoa, BS, thời gian, rồi PII riêng | `assets/vinmec-form-dang-ky-kham.png` | — | Tách chat/tool có LLM vs form PII không LLM |

## 3. User / review / social evidence

| Quote / review / observation | Nguồn | User là ai? | Pain/failure mode |
|---|---|---|---|
| "Chatbot chỉ gửi link, phải tự điền form dài" | Self-use (03/06/2026) | Người đặt khám Vinmec | Handoff / abandonment |
| "Hiện có lịch trống lúc 14:00 chiều nay" là thông tin user cần ngay sau khi biết khoa | Product hypothesis từ self-use | Người muốn đặt khám nhanh | Cần tool `getAvailableSlots()` thay vì chỉ gửi link |
| "Không biết đau bụng đi khoa nào" | Prompt thử nhóm | Người lần đầu | Cần AI gợi ý từ symptom |
| User có thể paste SĐT/email/CCCD ngay vào chat | Insight nhóm (privacy) | Mọi user | Client-side regex chặn PII trước server/LLM |
| Tên/mã thành viên khó chặn bằng regex chính xác | Risk analysis nhóm | Mọi user | Không regex tên trong chat; system prompt bỏ qua PII; chỉ nhập ở form |

```text
Review store: bổ sung 2 quote trước M1 Day 06.
```

## 4. Competitor / analog evidence

| App / mô hình | Họ xử lý thế nào? | Pattern cho prototype | 1 ngày? |
|---|---|---|---|
| Form Vinmec | Dropdown khoa, BS, ngày; PII section riêng | Pre-fill section đặt lịch; PII user tự điền | Có |
| MyVinmec | Wizard có cấu trúc | Agent = wizard trong chat | Có (mock) |
| Best practice AI + form | Tách inference vs transactional submit | `bookingDraft` → form, PII bypass LLM | Có |

## 5. Evidence -> Insight

```text
Evidence nổi bật:
- Chat thật: symptom không thành khoa/BS; chỉ link.
- Form thật: nhiều field; PII tách section — phù hợp form submit không LLM.

Insight:
User cần một luồng: mô tả bệnh → được gợi ý khoa/BS → form gần xong,
không phải nhập lại từ đầu và không phải đưa SĐT/email/CCCD/họ tên vào chat AI.

Opportunity:
AI agent + mock catalog trong chat;
tool call gợi ý khoa + lấy lịch trống;
handoff sang form đã fill cơ sở/khoa/slot/lý do khám, nhưng vẫn cho user đổi khoa nếu không ưng;
chỉ PII trên form, submit ngoài LLM, trả ticket ID
và cho xem/sửa thông tin người dùng ở tab lịch đã đặt.
```

## 6. Evidence đổi SPEC như thế nào?

- [x] Đổi build slice (từ "chỉ gợi ý khoa" → **agent + pre-fill form + privacy boundary**).
- [x] Đổi kiến trúc (2 phase: LLM / no-LLM).
- [x] Đổi deliverable Day 06 (chat + form + mock JSON).
- [x] Thêm fallback A/B/C: happy path, override khoa, escalation hotline/callback.
- [x] Thêm tầng privacy: frontend regex chặn SĐT/email/CCCD + system prompt bỏ qua PII.
- [ ] Đổi user chính (giữ nguyên).

```text
Trước: symptom → gợi ý 2–3 khoa → summary → link/form thủ công.
Sau: symptom → AI agent (mock khoa/BS/slot) → user chọn/override → form pre-fill/editable
→ user PII → submit mock → ticket ID + tab lịch đã đặt + edit thông tin.
Lý do: giải quyết trọn handoff + giảm rủi ro lộ PII; vẫn demo được 1 ngày với mock.
```
