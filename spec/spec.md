# SPEC sản phẩm - VinmecCare AI Agent đặt lịch

Thin SPEC này là bản chốt cho Day 06. Mục tiêu không phải build lại toàn bộ VinmecCare, mà chứng minh một lát cắt nhỏ: người bệnh mô tả triệu chứng trong chat, AI gợi ý chuyên khoa và lịch trống, sau đó chuyển sang form đặt lịch đã được điền sẵn phần không chứa thông tin cá nhân.

## 1. Track, sản phẩm và người dùng

**Track:** Healthcare  
**Sản phẩm thật tham chiếu:** Trợ lý ảo VinmecCare và form đăng ký khám Vinmec  
**Prototype Day 06:** Chatbot AI agent mock Vinmec, không tích hợp hệ thống production  
**LLM dùng cho prototype:** Gemini 3.1 Flash Lite  

**User cụ thể:** Người bệnh lần đầu đặt lịch khám, mô tả triệu chứng bằng tiếng Việt, không chắc mình nên chọn khoa hoặc bác sĩ nào.

**Bối cảnh:** Người dùng đang ở trong chat, muốn đặt lịch nhanh. Họ có thể mô tả triệu chứng như "đau bụng", "đau ngực", "chóng mặt", nhưng không biết nên chọn chuyên khoa nào trên form.

## 2. Bằng chứng

| Bằng chứng | Nguồn | Điều học được | SPEC phải đổi gì |
|---|---|---|---|
| User mô tả triệu chứng và muốn hẹn lịch, bot chỉ hỏi tuổi/năm sinh | `assets/vinmec-chat-01-trien-chung.png` | Chat hiện tại chưa biến triệu chứng thành quyết định đặt lịch | Agent cần hỏi thêm triệu chứng có cấu trúc |
| User trả lời năm sinh, bot hỏi cơ sở bệnh viện bằng free text | `assets/vinmec-chat-02-tuoi-co-so.png` | Flow dễ mơ hồ nếu user nhập tự do | Dùng mock facilities và lựa chọn rõ ràng |
| User chọn Vinmec ở Hà Nội, bot gửi link đặt khám và hotline | `assets/vinmec-chat-03-link-hotline.png` | Handoff sang link/hotline khiến user phải làm lại nhiều bước | Prototype cần mở form pre-fill có context |
| Form đăng ký khám Vinmec có nhiều field như cơ sở, khoa, bác sĩ, thời gian và thông tin cá nhân | Form Vinmec thật | Người dùng phải tự chọn nhiều field, dễ bỏ giữa chừng hoặc chọn sai | Tách phần AI gợi ý lịch với phần nhập PII |
| User có thể nhập SĐT/email/CCCD ngay trong chat | Risk analysis của nhóm | Nếu PII đi vào LLM hoặc transcript thì vượt sai ranh giới privacy | Frontend chặn PII bằng regex và system prompt bỏ qua PII |

Hiện nhóm có bằng chứng trực tiếp từ việc tự dùng VinmecCare và quan sát form thật. Nhóm chưa có review store hoặc phỏng vấn người dùng ngoài nhóm, nên các nhận định như "người dùng dễ bỏ giữa chừng" được xem là giả định sản phẩm dựa trên quan sát flow, không trình bày như dữ kiện định lượng.

## 3. Pain statement

Người bệnh lần đầu muốn đặt lịch khám qua chat nhưng gặp khó vì chatbot hiện tại chủ yếu điều hướng sang link, form hoặc hotline. Khi sang form, người dùng vẫn phải tự chọn chuyên khoa, bác sĩ, cơ sở và thời gian. Với triệu chứng mơ hồ, họ dễ không biết chọn khoa nào, chọn sai, hoặc phải gọi tư vấn viên thủ công.

Pain chính không chỉ là "cần chatbot trả lời tốt hơn", mà là:

```text
User cần một luồng từ mô tả triệu chứng -> gợi ý khoa/slot -> form gần hoàn tất,
không phải tự điền lại từ đầu và không đưa thông tin cá nhân vào chat AI.
```

## 4. Lát cắt để build

```text
Cho người bệnh lần đầu đang mô tả triệu chứng trong chat Vinmec mock,
prototype dùng Gemini 3.1 Flash Lite và mock tools để hỏi thêm tối đa 1-2 câu,
gợi ý 2-3 chuyên khoa phù hợp, lấy lịch trống theo khoa/cơ sở,
cho user chọn hoặc đổi chuyên khoa,
rồi mở form đặt lịch đã pre-fill cơ sở, khoa, slot, lý do khám và trạng thái.
User chỉ nhập họ tên, SĐT, email, ngày sinh ở form riêng; phần này không gửi vào LLM.
Sau khi submit, prototype trả ticket ID, lưu mock booking và cho xem/sửa thông tin trong tab "Lịch đã đặt".
```

Không build trong Day 06:

- API đặt lịch thật của Vinmec.
- OTP, thanh toán, bảo hiểm.
- Tích hợp VinBigdata/Vinmec production.
- Lưu PII vào vector DB hoặc fine-tune từ transcript.
- Đa ngôn ngữ hoặc multi-hospital đầy đủ.

## 5. AI Product Canvas

| Ô | Nội dung chốt |
|---|---|
| **Value** | AI giúp người bệnh chuyển từ triệu chứng mơ hồ sang lựa chọn khoa/slot cụ thể, giảm việc tự mò trên form. |
| **Trust** | AI chỉ gợi ý, không tự đặt lịch. User thấy lý do gợi ý, có thể đổi khoa/slot, hoặc chuyển sang callback/hotline nếu không chắc. |
| **Feasibility** | Demo được trong 1 ngày bằng Gemini + mock constants trong code, cộng 1 file lưu lịch sử đặt chỗ. Không cần API thật. |
| **Tín hiệu học** | Khi user override khoa hoặc sửa thông tin, prototype lưu lại event mock để nhóm dùng làm test case sau demo; PII không quay lại prompt. |

## 6. AI decision

AI chỉ ra quyết định hẹp:

```text
Map triệu chứng + tuổi/năm sinh + cơ sở mong muốn
-> rank 2-3 chuyên khoa phù hợp
-> giải thích ngắn lý do
-> gọi mock tool lấy slot trống
-> tạo bookingDraft hoặc callbackDraft.
```

Output mong muốn:

- `symptomSummary`
- `confidence`
- `redFlagRisk`
- `suggestedSpecialties`
- `bookingDraft`
- `callbackDraft` nếu cần escalation

## 7. Augment hay automate

- [x] **Augmentation:** AI gợi ý khoa, bác sĩ hoặc slot; user là người chọn.
- [x] **Conditional automation:** Agent tự điền phần không nhạy cảm của form từ `bookingDraft`.
- [ ] **Full automation:** Không tự submit lịch, không tự điền PII, không tự quyết định thay bác sĩ.

Lý do: đây là bối cảnh y tế và có rủi ro privacy. Nếu AI sai, hậu quả có thể là user chọn sai khoa hoặc chậm xử lý triệu chứng nặng. Vì vậy con người phải giữ quyền quyết định ở bước chọn lịch và nhập thông tin cá nhân.

## 8. Luồng sản phẩm

| Giai đoạn | Agent/UI làm gì | Output |
|---|---|---|
| 1. Intake triệu chứng | User nhập triệu chứng; AI hỏi thêm tối đa 1-2 câu về thời điểm, mức độ, vị trí đau, triệu chứng đi kèm | `symptomSummary`, `confidence`, `redFlagRisk` |
| 2. Gợi ý khoa và lịch | AI gọi `suggestSpecialty()` và `getAvailableSlots()` từ mock data | Danh sách khoa, lý do ngắn, slot trống |
| 3. User quyết định | User chọn khoa/slot hoặc override khoa | `bookingDraft` được cập nhật |
| 4. Form đặt lịch | UI mở form đã pre-fill cơ sở, khoa, slot, lý do khám; user nhập PII ở form riêng | Ticket ID sau submit |
| 5. Lịch đã đặt | Tab hiển thị booking mock; user có thể sửa thông tin liên hệ | Booking được cập nhật, không gọi LLM |

## 9. Ranh giới dữ liệu và privacy

Nguyên tắc chính:

```text
Chat AI chỉ nhận triệu chứng, tuổi/năm sinh, khu vực/cơ sở và thời gian mong muốn.
Họ tên, SĐT, email, CCCD/CMND không gửi vào prompt LLM.
PII chỉ được nhập ở form đặt lịch không dùng LLM.
```

### Frontend PII guard

| Loại PII | Pattern demo | Hành động |
|---|---|---|
| SĐT Việt Nam | `/(?:\+?84|0)(?:\d[\s.-]?){9}\b/` hoặc 10 chữ số liên tiếp | Disable nút gửi, yêu cầu xóa SĐT khỏi chat |
| Email | `/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i` | Disable nút gửi, yêu cầu xóa email |
| CCCD/CMND | `/\b\d{9}\b|\b\d{12}\b/` | Disable nút gửi, yêu cầu xóa CCCD/CMND |

Microcopy:

```text
Phát hiện thông tin cá nhân. Vui lòng xóa SĐT/email/CCCD khỏi tin nhắn.
AI chỉ cần biết triệu chứng; thông tin cá nhân sẽ được nhập ở form đặt lịch riêng.
```

### System prompt safeguard

```text
Bạn là AI booking agent cho Vinmec mock. Trong chat, chỉ thu thập triệu chứng,
tuổi/năm sinh, khu vực/cơ sở mong muốn và thời gian khám mong muốn.
Không yêu cầu hoặc lưu họ tên, số điện thoại, email, CCCD/CMND, mã thành viên.
Nếu user chủ động cung cấp PII, hãy bỏ qua hoàn toàn thông tin đó,
không nhắc lại trong câu trả lời, và nhắc user nhập thông tin cá nhân ở form riêng.
```

## 10. Bốn đường đi của trải nghiệm

| Đường đi | Prototype phải thể hiện |
|---|---|
| **Happy path** | User mô tả triệu chứng bình thường -> AI hỏi thêm -> gợi ý khoa + slot -> user đồng ý -> form pre-fill -> submit -> ticket ID |
| **AI không chắc** | Triệu chứng thiếu thông tin -> AI hỏi thêm hoặc đưa 2-3 lựa chọn thay vì tự tin quá mức |
| **User override** | User không đồng ý với khoa AI gợi ý -> user đổi khoa trong chat/form -> slot refresh theo khoa mới; có thể đánh dấu `Pending_Doctor_Review` |
| **Escalation/red flag** | Triệu chứng có dấu hiệu nặng -> không ép đặt lịch thường; hiển thị hotline hoặc callback form |
| **PII correction** | User nhập SĐT/email/CCCD trong chat -> frontend chặn trước khi gửi; nếu lọt qua, system prompt bỏ qua |

## 11. Failure mode nguy hiểm nhất

### Failure 1: AI gợi ý sai khoa cho triệu chứng nặng

Khi user mô tả dấu hiệu nguy hiểm như đau ngực dữ dội, khó thở, ngất, yếu liệt, chảy máu nhiều, AI có thể gợi ý nhầm khoa ngoại trú thay vì escalation. Hậu quả là user chậm được xử lý.

Mitigation trong prototype:

- Rule red flag chạy trước hoặc song song với LLM.
- Nếu có red flag, không tạo bookingDraft thường.
- Hiện hotline/callback và cảnh báo cần liên hệ y tế ngay.
- Lưu test case red flag trong demo.

### Failure 2: PII bị đưa vào chat

User có thể paste SĐT, email hoặc CCCD vào chat vì nghĩ chatbot cần thông tin đặt lịch.

Mitigation trong prototype:

- Frontend regex chặn trước khi gửi message.
- System prompt yêu cầu bỏ qua PII nếu lọt qua.
- PII chỉ nhập ở form Phase C không dùng LLM.

### Failure 3: User không tin hoặc không đồng ý với gợi ý AI

User có thể muốn chọn khoa khác vì đã có kinh nghiệm cá nhân hoặc được người nhà tư vấn.

Mitigation trong prototype:

- Cho override khoa trong chat hoặc form.
- Refresh slot theo khoa mới.
- Nếu override có rủi ro, đánh dấu `Pending_Doctor_Review`.

## 12. Mock data cần có

Làm tối giản như sau:

- `bookings.json` hoặc `bookings.csv`: file duy nhất để lưu lịch sử đã đặt.
- `facilities`, `specialties`, `doctors`, `slots`: hardcode trong code hoặc mock constants, không cần tách file riêng.

Nếu cần nhanh nhất cho demo, chỉ giữ một file persist là `bookings.json` và mọi dữ liệu còn lại nằm ngay trong source code.

### Schema thống nhất cho các file

| File | Trường |
|---|---|
| `facilities` | `facility_id`, `name`, `city`, `district`, `address`, `active` |
| `specialties` | `specialty_id`, `name`, `description`, `keywords`, `active` |
| `doctors` | `doctor_id`, `name`, `title`, `specialty_id`, `facility_id`, `active` |
| `slots` | `slot_id`, `facility_id`, `specialty_id`, `doctor_id`, `date`, `time`, `available` |
| `bookings` | `ticket_id`, `created_at`, `name`, `phone`, `email`, `dob`, `facility_id`, `specialty_id`, `doctor_id`, `slot_id`, `symptom_summary`, `status`, `notes`, `updated_at` |

Quy ước chung:

- Dùng snake_case cho tên cột.
- `*_id` là khóa chính/khóa ngoại để join giữa các file.
- `active` và `available` là boolean.
- `status` có thể là `draft`, `confirmed`, `callback`, `pending_review`, `cancelled`.
- Không lưu PII vào bất kỳ file nào ngoài `bookings`.

## 13. Kế hoạch kiểm thử và demo

### Test case 1: Happy path

Input:

```text
Tôi bị đau bụng âm ỉ từ hôm qua, muốn đặt lịch khám ở Vinmec Hà Nội.
```

Kỳ vọng:

- AI hỏi thêm 1-2 câu.
- Gợi ý khoa phù hợp.
- Hiển thị slot trống.
- User chọn slot.
- Form mở với khoa/slot/lý do đã pre-fill.
- Submit form trả ticket ID.

### Test case 2: PII trong chat

Input:

```text
Tôi đau bụng, số điện thoại của tôi là 0912345678.
```

Kỳ vọng:

- Frontend chặn gửi.
- Hiện microcopy yêu cầu xóa SĐT khỏi chat.
- Không gọi LLM.

### Test case 3: Red flag

Input:

```text
Tôi đau ngực dữ dội, khó thở và choáng.
```

Kỳ vọng:

- Prototype không gợi ý booking thường.
- Hiện hotline/callback.
- Tạo `callbackDraft` nếu user muốn tư vấn viên gọi lại.

### Test case 4: Override khoa

Input:

```text
Không, tôi muốn khám Tiêu hóa thay vì Nội tổng quát.
```

Kỳ vọng:

- AI/UI chấp nhận override.
- Slot refresh theo khoa mới.
- Booking có thể được đánh dấu `Pending_Doctor_Review` nếu cần.

## 14. Phân công

| Thành viên | Nhóm việc | Trách nhiệm chính | Deliverable |
|---|---|---|---|
|Lê Đàm Quân| UI/UX | Dựng giao diện chat, card gợi ý khoa/slot, form đặt lịch, tab lịch đã đặt, loading/error/warning states | Prototype nhìn được và chạy được end-to-end trên UI |
|Nguyễn Tiến Đạt| Call API / Agent | Tích hợp Gemini, viết system prompt, gửi message đã qua guard, nhận response có cấu trúc, xử lý lỗi API/fallback mock | Agent trả `symptomSummary`, `confidence`, `redFlagRisk`, `suggestedSpecialties` |
|Trần Nguyễn Đăng Khoa| Tool 1 - Medical routing tools | Chuẩn bị mock data y tế trong code, kiểm tra red flag bằng rule trong code, gợi ý chuyên khoa, lấy slot trống, xử lý override khoa | `suggestSpecialty`, `getAvailableSlots`, mock constants, Tạo data mẫu dựa theo các trường đã defined|
|Trần Hoàng Nam| Tool 2 - Booking/privacy tools | Chặn PII trong chat, tạo booking draft, submit booking mock, lưu/xem/sửa lịch đã đặt, đảm bảo PII không quay lại LLM | `piiGuard`, `createBookingDraft`, `submitBooking`, `listBookings`, `updateBooking` |

## 15. Demo script 3 phút

1. Nhập triệu chứng bình thường, không nhập PII trong chat.
2. Agent hỏi thêm 1-2 câu và gợi ý khoa/slot.
3. User chọn slot hoặc override khoa.
4. Form mở với draft đã có khoa, cơ sở, slot và lý do khám.
5. User nhập PII trong form riêng, submit và nhận ticket ID.
6. Mở tab "Lịch đã đặt", xem lại ticket và sửa thông tin liên hệ.
7. Thử nhập PII trong chat để thấy frontend guard.
8. Thử red flag để thấy hotline/callback.
