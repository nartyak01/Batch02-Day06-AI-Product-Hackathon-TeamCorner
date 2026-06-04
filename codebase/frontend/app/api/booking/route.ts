import { NextResponse } from "next/server";

const backendBaseUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = new URLSearchParams();
  const ticketId = searchParams.get("ticket_id");
  const name = searchParams.get("name");
  const phone = searchParams.get("phone");
  const email = searchParams.get("email");
  const dob = searchParams.get("dob");
  const status = searchParams.get("status");
  if (ticketId) query.set("ticket_id", ticketId);
  if (name) query.set("name", name);
  if (phone) query.set("phone", phone);
  if (email) query.set("email", email);
  if (dob) query.set("dob", dob);
  if (status) query.set("status", status);

  const response = await fetch(`${backendBaseUrl}/bookings?${query.toString()}`);
  const data = await response.json();
  if (!response.ok) {
    return NextResponse.json(
      { error: data.error ?? "Backend bookings error" },
      { status: response.status }
    );
  }
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const response = await fetch(`${backendBaseUrl}/bookings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const result = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: result.error ?? result.message ?? "Booking error" },
        { status: response.status }
      );
    }

    const detailResponse = await fetch(`${backendBaseUrl}/bookings/${result.ticket_id}`);
    const detailData = await detailResponse.json();
    const booking = detailData.booking ?? result.booking;
    const slot = booking
      ? {
          slot_id: booking.slot_id,
          facility_id: booking.facility_id,
          specialty_id: booking.specialty_id,
          doctor_id: booking.doctor_id,
          date: booking.slot_date,
          time: booking.slot_time,
          available: "false",
          facility_name: booking.facility_name,
          specialty_name: booking.specialty_name,
          doctor_name: booking.doctor_name,
          doctor_title: booking.doctor_title ?? "Bác sĩ"
        }
      : null;

    return NextResponse.json({
      action: {
        type: "booking_success",
        message: `Đặt lịch thành công. Ticket của bạn là ${result.ticket_id}.`,
        booking,
        slot
      }
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Booking error" },
      { status: 409 }
    );
  }
}

export async function PATCH(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const ticketId = searchParams.get("ticket_id");
    if (!ticketId) {
      return NextResponse.json({ error: "ticket_id is required" }, { status: 400 });
    }

    const body = await request.json();
    const response = await fetch(`${backendBaseUrl}/bookings/${ticketId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { error: data.error ?? data.message ?? "Update booking error" },
        { status: response.status }
      );
    }
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Update booking error" },
      { status: 400 }
    );
  }
}
