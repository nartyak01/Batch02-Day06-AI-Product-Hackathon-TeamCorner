import { NextResponse } from "next/server";
import { getAvailableSlots } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const facilityId = searchParams.get("facility_id");
  const specialtyId = searchParams.get("specialty_id");

  if (!facilityId || !specialtyId) {
    return NextResponse.json(
      { error: "facility_id and specialty_id are required" },
      { status: 400 }
    );
  }

  return NextResponse.json({
    slots: await getAvailableSlots(facilityId, specialtyId)
  });
}
