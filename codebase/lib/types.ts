export type Facility = {
  facility_id: string;
  name: string;
  city: string;
  district: string;
  address: string;
  active: string;
};

export type Specialty = {
  specialty_id: string;
  name: string;
  description: string;
  keywords: string;
  active: string;
};

export type Doctor = {
  doctor_id: string;
  name: string;
  title: string;
  specialty_id: string;
  facility_id: string;
  active: string;
};

export type Slot = {
  slot_id: string;
  facility_id: string;
  specialty_id: string;
  doctor_id: string;
  date: string;
  time: string;
  available: string;
};

export type Booking = {
  ticket_id: string;
  created_at: string;
  name: string;
  phone: string;
  email: string;
  dob: string;
  facility_id: string;
  specialty_id: string;
  doctor_id: string;
  slot_id: string;
  symptom_summary: string;
  status: string;
  notes: string;
  updated_at: string;
};

export type BookingDraft = {
  facility_id: string;
  specialty_id: string;
  doctor_id?: string;
  slot_id?: string;
  symptom_summary: string;
  notes?: string;
  status?: string;
};

export type EnrichedSlot = Slot & {
  facility_name: string;
  specialty_name: string;
  doctor_name: string;
  doctor_title: string;
};

export type SpecialtySuggestion = Specialty & {
  score: number;
  reason: string;
};

export type AgentAction =
  | {
      type: "ask_clarifying_question";
      message: string;
      quickReplies?: string[];
    }
  | {
      type: "suggest_specialties";
      message: string;
      suggestions: SpecialtySuggestion[];
      facilities: Facility[];
      symptomSummary: string;
    }
  | {
      type: "show_slots";
      message: string;
      slots: EnrichedSlot[];
      draft: BookingDraft;
    }
  | {
      type: "confirm_slot";
      message: string;
      slot: EnrichedSlot;
      draft: BookingDraft;
    }
  | {
      type: "render_booking_form";
      message: string;
      slot: EnrichedSlot;
      draft: BookingDraft;
    }
  | {
      type: "escalate_callback";
      message: string;
      hotline: string;
      reason: string;
    }
  | {
      type: "booking_success";
      message: string;
      booking: Booking;
      slot: EnrichedSlot;
    };

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};
