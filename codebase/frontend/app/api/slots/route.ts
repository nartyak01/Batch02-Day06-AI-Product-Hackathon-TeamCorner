import { NextResponse } from "next/server";

const backendBaseUrl = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const facilityId = searchParams.get("facility_id");
  const specialtyId = searchParams.get("specialty_id");
  const doctorId = searchParams.get("doctor_id") ?? undefined;

  if (!facilityId || !specialtyId) {
    return NextResponse.json(
      { error: "facility_id and specialty_id are required" },
      { status: 400 }
    );
  }

  const response = await fetch(`${backendBaseUrl}/tools/available-slots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      specialty_id: specialtyId,
      facility_id: facilityId,
      doctor_id: doctorId
    })
  });
  const data = await response.json();
  if (!response.ok) {
    return NextResponse.json(
      { error: data.error ?? "Slot error" },
      { status: response.status }
    );
  }

  return NextResponse.json({ slots: data.slots ?? [] });
}
