import { appendCsv, readCsv, writeCsv } from "./csv";
import type {
  Booking,
  BookingDraft,
  Doctor,
  EnrichedSlot,
  Facility,
  Slot,
  Specialty,
  SpecialtySuggestion
} from "./types";

const bookingHeaders = [
  "ticket_id",
  "created_at",
  "name",
  "phone",
  "email",
  "dob",
  "facility_id",
  "specialty_id",
  "doctor_id",
  "slot_id",
  "symptom_summary",
  "status",
  "notes",
  "updated_at"
];

const slotHeaders = [
  "slot_id",
  "facility_id",
  "specialty_id",
  "doctor_id",
  "date",
  "time",
  "available"
];

export async function getFacilities() {
  return (await readCsv<Facility>("facilities.csv")).filter((item) => item.active === "true");
}

export async function getSpecialties() {
  return (await readCsv<Specialty>("specialties.csv")).filter((item) => item.active === "true");
}

export async function getDoctors() {
  return (await readCsv<Doctor>("doctors.csv")).filter((item) => item.active === "true");
}

export async function getSlots() {
  return await readCsv<Slot>("slots.csv");
}

export async function getEnrichedSlot(slotId: string): Promise<EnrichedSlot | null> {
  const [slots, facilities, specialties, doctors] = await Promise.all([
    getSlots(),
    getFacilities(),
    getSpecialties(),
    getDoctors()
  ]);
  const slot = slots.find((item) => item.slot_id === slotId);
  if (!slot) return null;
  return enrichSlot(slot, facilities, specialties, doctors);
}

export async function suggestSpecialties(input: string): Promise<SpecialtySuggestion[]> {
  const specialties = await getSpecialties();
  const normalized = normalize(input);

  const scored = specialties.map((specialty) => {
    const keywords = specialty.keywords.split(";").map((keyword) => keyword.trim());
    const matches = keywords.filter((keyword) => normalized.includes(normalize(keyword)));
    const nameMatch = normalized.includes(normalize(specialty.name)) ? 2 : 0;
    const score = matches.length + nameMatch;
    const reason =
      matches.length > 0
        ? `Khớp với dấu hiệu: ${matches.slice(0, 3).join(", ")}`
        : "Phù hợp để sàng lọc ban đầu dựa trên mô tả triệu chứng.";
    return { ...specialty, score, reason };
  });

  const ranked = scored
    .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, "vi"))
    .slice(0, 3);

  if (ranked.every((item) => item.score === 0)) {
    return scored
      .filter((item) =>
        ["spec_general", "spec_emergency", "spec_digestive"].includes(item.specialty_id)
      )
      .map((item, index) => ({
        ...item,
        score: 1 - index * 0.1,
        reason: "Chưa đủ chắc chắn, nên bắt đầu bằng khám tổng quát hoặc sàng lọc."
      }));
  }

  return ranked;
}

export async function getAvailableSlots(
  facilityId: string,
  specialtyId: string
): Promise<EnrichedSlot[]> {
  const [slots, facilities, specialties, doctors] = await Promise.all([
    getSlots(),
    getFacilities(),
    getSpecialties(),
    getDoctors()
  ]);

  return slots
    .filter(
      (slot) =>
        slot.available === "true" &&
        slot.facility_id === facilityId &&
        slot.specialty_id === specialtyId
    )
    .map((slot) => enrichSlot(slot, facilities, specialties, doctors))
    .slice(0, 5);
}

export async function createBooking(
  payload: {
    name: string;
    phone: string;
    email: string;
    dob: string;
    notes?: string;
  } & BookingDraft
): Promise<{ booking: Booking; slot: EnrichedSlot }> {
  if (!payload.slot_id || !payload.doctor_id) {
    throw new Error("Thiếu bác sĩ hoặc khung giờ.");
  }

  const slots = await getSlots();
  const slot = slots.find((item) => item.slot_id === payload.slot_id);
  if (!slot || slot.available !== "true") {
    throw new Error("Khung giờ này vừa được đặt. Vui lòng chọn khung giờ khác.");
  }

  const now = new Date().toISOString();
  const ticketId = `VIN-${Date.now().toString().slice(-8)}`;
  const booking: Booking = {
    ticket_id: ticketId,
    created_at: now,
    name: payload.name,
    phone: payload.phone,
    email: payload.email,
    dob: payload.dob,
    facility_id: payload.facility_id,
    specialty_id: payload.specialty_id,
    doctor_id: payload.doctor_id,
    slot_id: payload.slot_id,
    symptom_summary: payload.symptom_summary,
    status: payload.status ?? "CONFIRMED",
    notes: payload.notes ?? "",
    updated_at: now
  };

  await appendCsv("bookings.csv", booking, bookingHeaders);
  await writeCsv(
    "slots.csv",
    slots.map((item) =>
      item.slot_id === payload.slot_id ? { ...item, available: "false" } : item
    ),
    slotHeaders
  );

  const enriched = await getEnrichedSlot(payload.slot_id);
  if (!enriched) throw new Error("Không tìm thấy thông tin khung giờ sau khi đặt.");

  return { booking, slot: { ...enriched, available: "false" } };
}

export async function getDefaultFacility(facilityId?: string) {
  const facilities = await getFacilities();
  return (
    facilities.find((facility) => facility.facility_id === facilityId) ??
    facilities.find((facility) => facility.facility_id === "fac_times_city") ??
    facilities[0]
  );
}

function enrichSlot(
  slot: Slot,
  facilities: Facility[],
  specialties: Specialty[],
  doctors: Doctor[]
): EnrichedSlot {
  const facility = facilities.find((item) => item.facility_id === slot.facility_id);
  const specialty = specialties.find((item) => item.specialty_id === slot.specialty_id);
  const doctor = doctors.find((item) => item.doctor_id === slot.doctor_id);

  return {
    ...slot,
    facility_name: facility?.name ?? slot.facility_id,
    specialty_name: specialty?.name ?? slot.specialty_id,
    doctor_name: doctor?.name ?? slot.doctor_id,
    doctor_title: doctor?.title ?? "Bác sĩ"
  };
}

export function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d");
}
