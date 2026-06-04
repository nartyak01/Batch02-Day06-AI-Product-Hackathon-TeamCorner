import { NextResponse } from "next/server";
import { createBooking } from "@/lib/data";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const required = [
      "name",
      "phone",
      "email",
      "dob",
      "facility_id",
      "specialty_id",
      "doctor_id",
      "slot_id",
      "symptom_summary"
    ];

    const missing = required.filter((key) => !body[key]);
    if (missing.length > 0) {
      return NextResponse.json(
        { error: `Thiếu trường: ${missing.join(", ")}` },
        { status: 400 }
      );
    }

    const result = await createBooking(body);
    return NextResponse.json({
      action: {
        type: "booking_success",
        message: `Đặt lịch thành công. Ticket của bạn là ${result.booking.ticket_id}.`,
        ...result
      }
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Booking error" },
      { status: 409 }
    );
  }
}
