import {
  getAvailableSlots,
  getDefaultFacility,
  getFacilities,
  getSpecialties,
  suggestSpecialties
} from "./data";
import type { AgentAction, BookingDraft, ChatMessage } from "./types";

const redFlagPattern =
  /đau ngực|kho tho|khó thở|ngất|liệt|co giật|chảy máu|sot cao|sốt cao|tai nạn|đột quỵ|dot quy|tự tử|tu tu|cấp cứu|cap cuu/i;

export const piiPatterns = {
  phone: /(?:\+?84|0)(?:\d[\s.-]?){8,10}\b|\b\d{10,11}\b/,
  email: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
  nationalId: /\b\d{9}\b|\b\d{12}\b/
};

export function detectPii(text: string) {
  const found = Object.entries(piiPatterns)
    .filter(([, pattern]) => pattern.test(text))
    .map(([key]) => key);
  return {
    hasPii: found.length > 0,
    found
  };
}

export async function buildAgentAction(
  messages: ChatMessage[],
  draft?: Partial<BookingDraft>
): Promise<AgentAction> {
  const lastUserText =
    [...messages].reverse().find((message) => message.role === "user")?.content ?? "";

  if (detectPii(lastUserText).hasPii) {
    return {
      type: "ask_clarifying_question",
      message:
        "Mình phát hiện thông tin cá nhân trong chat. Vui lòng xóa SĐT/email/CCCD khỏi tin nhắn; bạn sẽ nhập các thông tin đó ở form đặt lịch riêng.",
      quickReplies: ["Tôi sẽ chỉ mô tả triệu chứng", "Mở lại hướng dẫn"]
    };
  }

  if (redFlagPattern.test(lastUserText)) {
    return {
      type: "escalate_callback",
      message:
        "Triệu chứng bạn mô tả có dấu hiệu cần được hỗ trợ khẩn. Prototype sẽ không tự chọn khoa trong trường hợp này. Vui lòng gọi tổng đài Vinmec hoặc để tư vấn viên gọi lại.",
      hotline: "024 3975 6789",
      reason: "red_flag_symptom"
    };
  }

  const geminiSummary = await tryGeminiSummary(messages);
  const symptomSummary = geminiSummary || summarizeLocally(messages);
  const facility = await getDefaultFacility(draft?.facility_id);
  const suggestions = await suggestSpecialties(symptomSummary);
  const selectedSpecialtyId = draft?.specialty_id ?? suggestions[0]?.specialty_id;

  if (!selectedSpecialtyId) {
    return {
      type: "ask_clarifying_question",
      message: "Bạn mô tả thêm triệu chứng chính, thời gian xuất hiện và mức độ khó chịu giúp mình nhé.",
      quickReplies: ["Đau bụng 2 ngày", "Ho sốt từ tối qua", "Đau ngực khó thở"]
    };
  }

  const slots = await getAvailableSlots(facility.facility_id, selectedSpecialtyId);
  if (slots.length > 0) {
    return {
      type: "show_slots",
      message: `Dựa trên mô tả, mình đề xuất ${suggestions[0].name}. Bạn chọn một khung giờ còn trống để mình xác nhận trước khi mở form nhé.`,
      slots,
      draft: {
        facility_id: facility.facility_id,
        specialty_id: selectedSpecialtyId,
        symptom_summary: symptomSummary,
        status: "DRAFT",
        notes: suggestions[0].reason
      }
    };
  }

  return {
    type: "suggest_specialties",
    message:
      "Mình đã tìm được chuyên khoa phù hợp, nhưng cơ sở mặc định chưa có slot trống. Bạn có thể đổi cơ sở hoặc chọn chuyên khoa khác.",
    suggestions,
    facilities: await getFacilities(),
    symptomSummary
  };
}

export async function getReferenceData() {
  const [facilities, specialties] = await Promise.all([getFacilities(), getSpecialties()]);
  return { facilities, specialties };
}

async function tryGeminiSummary(messages: ChatMessage[]) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return null;

  const model = process.env.GEMINI_MODEL || "gemini-1.5-flash";
  const recent = messages
    .slice(-6)
    .map((message) => `${message.role === "user" ? "User" : "Assistant"}: ${message.content}`)
    .join("\n");

  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              role: "user",
              parts: [
                {
                  text: `${systemPrompt}\n\nTóm tắt triệu chứng và bối cảnh đặt lịch thành một câu ngắn, không bao gồm PII:\n${recent}`
                }
              ]
            }
          ],
          generationConfig: {
            temperature: 0.2,
            maxOutputTokens: 120
          }
        })
      }
    );

    if (!response.ok) return null;
    const data = await response.json();
    return data?.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || null;
  } catch {
    return null;
  }
}

function summarizeLocally(messages: ChatMessage[]) {
  const userMessages = messages
    .filter((message) => message.role === "user")
    .map((message) => message.content)
    .join(" ");
  return userMessages.slice(0, 240) || "Người dùng cần tư vấn chọn chuyên khoa và đặt lịch khám.";
}

const systemPrompt = `
Bạn là AI booking agent cho Vinmec mock prototype.
Nhiệm vụ: hỗ trợ người dùng mô tả triệu chứng, chọn chuyên khoa/cơ sở/bác sĩ/slot từ dữ liệu mock, xác nhận khung giờ, rồi render form đặt lịch.
Ranh giới dữ liệu: trong chat chỉ thu triệu chứng, tuổi hoặc năm sinh, khu vực/cơ sở mong muốn, thời gian khám mong muốn.
Không yêu cầu, không lưu, không nhắc lại họ tên, số điện thoại, email, CCCD/CMND hoặc mã thành viên trong chat.
Nếu người dùng đưa PII, bỏ qua hoàn toàn và nhắc họ nhập thông tin cá nhân ở form riêng.
Không tự submit đặt lịch. Luôn yêu cầu người dùng xác nhận slot trước khi mở form.
Nếu có dấu hiệu cấp cứu hoặc red flag, không ép đặt lịch thường; chuyển hotline/callback.
Khi không chắc chắn, hỏi thêm tối đa 2 câu hoặc đề xuất khám tổng quát.
`;
