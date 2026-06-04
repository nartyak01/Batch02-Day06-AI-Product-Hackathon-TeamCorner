import { NextResponse } from "next/server";
import type { BookingDraft, ChatMessage } from "@/lib/types";

const backendBaseUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET() {
  const response = await fetch(`${backendBaseUrl}/reference-data`);
  const data = await response.json();
  if (!response.ok) {
    return NextResponse.json(
      { error: data.error ?? "Backend reference-data error" },
      { status: response.status }
    );
  }
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      messages?: ChatMessage[];
      draft?: Partial<BookingDraft>;
      context?: Record<string, unknown>;
    };

    const messages = body.messages ?? [];
    if (messages.length === 0) {
      return NextResponse.json({ error: "messages is required" }, { status: 400 });
    }

    const userMessage = [...messages].reverse().find((message) => message.role === "user")?.content ?? "";
    const response = await fetch(`${backendBaseUrl}/agent/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_message: userMessage,
        history: messages,
        context: {
          ...body.context,
          ...body.draft,
          selected_slot_id: body.draft?.slot_id,
          selected_specialty_id: body.draft?.specialty_id
        }
      })
    });
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: data.error ?? "Backend agent error" },
        { status: response.status }
      );
    }

    return NextResponse.json({ action: mapAgentResponseToAction(data), meta: data.meta ?? {} });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Agent error" },
      { status: 500 }
    );
  }
}

function mapAgentResponseToAction(result: any) {
  if (result?.callback_draft || result?.state === "escalation") {
    return {
      type: "escalate_callback",
      message: result?.reply ?? "Triệu chứng cần hỗ trợ khẩn.",
      hotline: result?.callback_draft?.hotline ?? "1900 56 56 56",
      reason:
        result?.callback_draft?.reason_for_callback ??
        result?.callback_draft?.status ??
        "red_flag_symptom"
    };
  }

  if (result?.needs_more_info || result?.state === "need_more_info") {
    return {
      type: "ask_clarifying_question",
      message: result?.reply ?? "Mình cần thêm thông tin.",
      questions: result?.questions?.slice(0, 3) ?? []
    };
  }

  if (Array.isArray(result?.slots) && result.slots.length > 0) {
    return {
      type: "show_slots",
      message: result?.reply ?? "Đây là các slot còn trống.",
      slots: result.slots,
      draft:
        result?.booking_draft ?? {
          facility_id: result?.booking_draft?.facility_id ?? "",
          specialty_id: result?.booking_draft?.specialty_id ?? "",
          symptom_summary: result?.symptom_summary ?? "",
          status: "draft",
          notes: ""
        }
    };
  }

  if (Array.isArray(result?.suggested_specialties) && result.suggested_specialties.length > 0) {
    return {
      type: "suggest_specialties",
      message: result?.reply ?? "Mình có vài gợi ý chuyên khoa.",
      suggestions: result.suggested_specialties,
      facilities: [],
      symptomSummary: result?.symptom_summary ?? ""
    };
  }

  return {
    type: "ask_clarifying_question",
    message: result?.reply ?? "Mình cần thêm thông tin.",
    questions: result?.questions?.slice(0, 3) ?? []
  };
}
