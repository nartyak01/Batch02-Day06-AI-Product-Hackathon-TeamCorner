import { NextResponse } from "next/server";
import { buildAgentAction, getReferenceData } from "@/lib/agent";
import type { BookingDraft, ChatMessage } from "@/lib/types";

export async function GET() {
  return NextResponse.json(await getReferenceData());
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      messages?: ChatMessage[];
      draft?: Partial<BookingDraft>;
    };

    const messages = body.messages ?? [];
    if (messages.length === 0) {
      return NextResponse.json(
        { error: "messages is required" },
        { status: 400 }
      );
    }

    const action = await buildAgentAction(messages, body.draft);
    return NextResponse.json({ action });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Agent error" },
      { status: 500 }
    );
  }
}
