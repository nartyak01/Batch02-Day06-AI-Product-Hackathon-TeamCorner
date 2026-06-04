"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type {
  AgentAction,
  BookingDraft,
  ChatMessage,
  EnrichedSlot,
  Facility,
  Specialty
} from "@/lib/types";

type UiMessage = ChatMessage & {
  id: string;
  action?: AgentAction;
};

const piiPatterns = {
  phone: /(?:\+?84|0)(?:\d[\s.-]?){8,10}\b|\b\d{10,11}\b/,
  email: /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
  nationalId: /\b\d{9}\b|\b\d{12}\b/
};

const initialAssistant: UiMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Xin chào, mình là trợ lý đặt lịch Vinmec mock. Bạn đang gặp triệu chứng gì và muốn khám ở khu vực nào?"
};

export default function Home() {
  const [messages, setMessages] = useState<UiMessage[]>([initialAssistant]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const piiWarning = useMemo(() => detectPii(input), [input]);

  useEffect(() => {
    fetch("/api/agent")
      .then((response) => response.json())
      .then((data) => {
        setFacilities(data.facilities ?? []);
        setSpecialties(data.specialties ?? []);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [messages, isLoading]);

  async function submitMessage(event?: FormEvent, quickText?: string) {
    event?.preventDefault();
    const text = (quickText ?? input).trim();
    if (!text || detectPii(text)) return;

    const userMessage: UiMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text
    };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map(({ role, content }) => ({ role, content }))
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Agent error");
      pushAssistant(data.action.message, data.action);
    } catch (error) {
      pushAssistant(
        error instanceof Error
          ? error.message
          : "Mình chưa xử lý được yêu cầu này. Bạn thử lại giúp mình nhé."
      );
    } finally {
      setIsLoading(false);
    }
  }

  function pushAssistant(content: string, action?: AgentAction) {
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content,
        action
      }
    ]);
  }

  function confirmSlot(slot: EnrichedSlot, draft: BookingDraft) {
    const confirmedDraft = {
      ...draft,
      facility_id: slot.facility_id,
      specialty_id: slot.specialty_id,
      doctor_id: slot.doctor_id,
      slot_id: slot.slot_id
    };
    pushAssistant(`Bạn xác nhận khung ${slot.time} ngày ${formatDate(slot.date)} tại ${slot.facility_name}?`, {
      type: "confirm_slot",
      message: `Bạn xác nhận khung ${slot.time} ngày ${formatDate(slot.date)} tại ${slot.facility_name}?`,
      slot,
      draft: confirmedDraft
    });
  }

  function renderForm(slot: EnrichedSlot, draft: BookingDraft) {
    pushAssistant("Mình đã giữ tạm khung giờ này. Bạn điền thông tin cá nhân trong form bảo mật riêng bên dưới.", {
      type: "render_booking_form",
      message:
        "Mình đã giữ tạm khung giờ này. Bạn điền thông tin cá nhân trong form bảo mật riêng bên dưới.",
      slot,
      draft
    });
  }

  async function refreshSlots(facilityId: string, specialtyId: string, symptomSummary: string) {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        facility_id: facilityId,
        specialty_id: specialtyId
      });
      const response = await fetch(`/api/slots?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Slot error");
      const specialty = specialties.find((item) => item.specialty_id === specialtyId);
      pushAssistant(`Mình đã tải khung giờ cho ${specialty?.name ?? "chuyên khoa đã chọn"}.`, {
        type: "show_slots",
        message: `Mình đã tải khung giờ cho ${specialty?.name ?? "chuyên khoa đã chọn"}.`,
        slots: data.slots,
        draft: {
          facility_id: facilityId,
          specialty_id: specialtyId,
          symptom_summary: symptomSummary,
          status: "DRAFT",
          notes: "User override specialty/facility"
        }
      });
    } catch (error) {
      pushAssistant(
        error instanceof Error
          ? error.message
          : "Chưa tải được khung giờ cho lựa chọn này."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="context-panel">
          <div className="brand-lockup">
            <div className="brand-mark">V</div>
            <div>
              <p className="eyebrow">VinmecCare mock</p>
              <h1>AI Booking Agent</h1>
            </div>
          </div>

          <div className="status-stack">
            <div>
              <span className="status-dot" />
              Gemini server-side
            </div>
            <div>
              <span className="status-dot alt" />
              CSV booking database
            </div>
            <div>
              <span className="status-dot warn" />
              PII guard before LLM
            </div>
          </div>

          <div className="quick-panel">
            <p>Demo cases</p>
            {[
              "Tôi đau bụng và buồn nôn từ hôm qua, muốn khám ở Times City",
              "Bé nhà tôi sốt và ho từ tối qua",
              "Tôi đau đầu, chóng mặt, mất ngủ vài ngày",
              "Tôi đau ngực và khó thở"
            ].map((text) => (
              <button key={text} type="button" onClick={() => submitMessage(undefined, text)}>
                {text}
              </button>
            ))}
          </div>
        </aside>

        <section className="chat-panel">
          <header className="chat-header">
            <div>
              <p className="eyebrow">Checkpoint 1</p>
              <h2>Đặt lịch khám từ triệu chứng</h2>
            </div>
            <span className="session-pill">Session mock</span>
          </header>

          <div className="messages" ref={scrollRef}>
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                facilities={facilities}
                specialties={specialties}
                onQuickReply={(text) => submitMessage(undefined, text)}
                onConfirmSlot={confirmSlot}
                onRenderForm={renderForm}
                onRefreshSlots={refreshSlots}
                onBookingSuccess={(action) => pushAssistant(action.message, action)}
              />
            ))}
            {isLoading ? (
              <div className="message assistant">
                <div className="avatar">AI</div>
                <div className="bubble typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            ) : null}
          </div>

          <form className="composer" onSubmit={submitMessage}>
            {piiWarning ? (
              <div className="pii-warning">
                Phát hiện SĐT/email/CCCD trong chat. Vui lòng xóa thông tin cá nhân và chỉ nhập
                triệu chứng.
              </div>
            ) : null}
            <div className="composer-row">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Mô tả triệu chứng, tuổi/năm sinh, cơ sở mong muốn..."
              />
              <button disabled={!input.trim() || Boolean(piiWarning) || isLoading} type="submit">
                Gửi
              </button>
            </div>
          </form>
        </section>
      </section>
    </main>
  );
}

function MessageBubble({
  message,
  facilities,
  specialties,
  onQuickReply,
  onConfirmSlot,
  onRenderForm,
  onRefreshSlots,
  onBookingSuccess
}: {
  message: UiMessage;
  facilities: Facility[];
  specialties: Specialty[];
  onQuickReply: (text: string) => void;
  onConfirmSlot: (slot: EnrichedSlot, draft: BookingDraft) => void;
  onRenderForm: (slot: EnrichedSlot, draft: BookingDraft) => void;
  onRefreshSlots: (facilityId: string, specialtyId: string, symptomSummary: string) => void;
  onBookingSuccess: (action: AgentAction) => void;
}) {
  const isAssistant = message.role === "assistant";

  return (
    <div className={`message ${message.role}`}>
      {isAssistant ? <div className="avatar">AI</div> : null}
      <div className="bubble">
        <p>{message.content}</p>
        {message.action ? (
          <ActionCard
            action={message.action}
            facilities={facilities}
            specialties={specialties}
            onQuickReply={onQuickReply}
            onConfirmSlot={onConfirmSlot}
            onRenderForm={onRenderForm}
            onRefreshSlots={onRefreshSlots}
            onBookingSuccess={onBookingSuccess}
          />
        ) : null}
      </div>
    </div>
  );
}

function ActionCard({
  action,
  facilities,
  specialties,
  onQuickReply,
  onConfirmSlot,
  onRenderForm,
  onRefreshSlots,
  onBookingSuccess
}: {
  action: AgentAction;
  facilities: Facility[];
  specialties: Specialty[];
  onQuickReply: (text: string) => void;
  onConfirmSlot: (slot: EnrichedSlot, draft: BookingDraft) => void;
  onRenderForm: (slot: EnrichedSlot, draft: BookingDraft) => void;
  onRefreshSlots: (facilityId: string, specialtyId: string, symptomSummary: string) => void;
  onBookingSuccess: (action: AgentAction) => void;
}) {
  if (action.type === "ask_clarifying_question") {
    return (
      <div className="quick-replies">
        {action.quickReplies?.map((reply) => (
          <button key={reply} type="button" onClick={() => onQuickReply(reply)}>
            {reply}
          </button>
        ))}
      </div>
    );
  }

  if (action.type === "suggest_specialties") {
    return (
      <div className="tool-card">
        <SpecialtyOverride
          facilities={facilities}
          specialties={specialties}
          defaultFacilityId={facilities[0]?.facility_id ?? ""}
          defaultSpecialtyId={action.suggestions[0]?.specialty_id ?? ""}
          symptomSummary={action.symptomSummary}
          onRefreshSlots={onRefreshSlots}
        />
      </div>
    );
  }

  if (action.type === "show_slots") {
    return (
      <div className="tool-card">
        <div className="slot-grid">
          {action.slots.length > 0 ? (
            action.slots.map((slot) => (
              <button
                className="slot-card"
                key={slot.slot_id}
                type="button"
                onClick={() => onConfirmSlot(slot, action.draft)}
              >
                <strong>
                  {slot.time} · {formatDate(slot.date)}
                </strong>
                <span>{slot.doctor_title} {slot.doctor_name}</span>
                <span>{slot.facility_name}</span>
              </button>
            ))
          ) : (
            <p className="muted">Chưa có khung giờ trống cho lựa chọn này.</p>
          )}
        </div>
        <SpecialtyOverride
          facilities={facilities}
          specialties={specialties}
          defaultFacilityId={action.draft.facility_id}
          defaultSpecialtyId={action.draft.specialty_id}
          symptomSummary={action.draft.symptom_summary}
          onRefreshSlots={onRefreshSlots}
        />
      </div>
    );
  }

  if (action.type === "confirm_slot") {
    return (
      <div className="tool-card compact">
        <TicketPreview slot={action.slot} />
        <button className="primary-action" type="button" onClick={() => onRenderForm(action.slot, action.draft)}>
          Xác nhận khung giờ
        </button>
      </div>
    );
  }

  if (action.type === "render_booking_form") {
    return (
      <BookingForm
        slot={action.slot}
        draft={action.draft}
        onBookingSuccess={onBookingSuccess}
      />
    );
  }

  if (action.type === "escalate_callback") {
    return (
      <div className="tool-card urgent">
        <strong>Tổng đài: {action.hotline}</strong>
        <span>Mã xử lý: {action.reason}</span>
      </div>
    );
  }

  if (action.type === "booking_success") {
    return (
      <div className="ticket-card">
        <p className="eyebrow">Ticket</p>
        <h3>{action.booking.ticket_id}</h3>
        <TicketPreview slot={action.slot} />
        <div className="ticket-meta">
          <span>Trạng thái: {action.booking.status}</span>
          <span>Người đặt: {action.booking.name}</span>
        </div>
      </div>
    );
  }

  return null;
}

function SpecialtyOverride({
  facilities,
  specialties,
  defaultFacilityId,
  defaultSpecialtyId,
  symptomSummary,
  onRefreshSlots
}: {
  facilities: Facility[];
  specialties: Specialty[];
  defaultFacilityId: string;
  defaultSpecialtyId: string;
  symptomSummary: string;
  onRefreshSlots: (facilityId: string, specialtyId: string, symptomSummary: string) => void;
}) {
  const [facilityId, setFacilityId] = useState(defaultFacilityId);
  const [specialtyId, setSpecialtyId] = useState(defaultSpecialtyId);

  return (
    <div className="override-row">
      <select value={facilityId} onChange={(event) => setFacilityId(event.target.value)}>
        {facilities.map((facility) => (
          <option key={facility.facility_id} value={facility.facility_id}>
            {facility.name}
          </option>
        ))}
      </select>
      <select value={specialtyId} onChange={(event) => setSpecialtyId(event.target.value)}>
        {specialties.map((specialty) => (
          <option key={specialty.specialty_id} value={specialty.specialty_id}>
            {specialty.name}
          </option>
        ))}
      </select>
      <button type="button" onClick={() => onRefreshSlots(facilityId, specialtyId, symptomSummary)}>
        Tải slot
      </button>
    </div>
  );
}

function BookingForm({
  slot,
  draft,
  onBookingSuccess
}: {
  slot: EnrichedSlot;
  draft: BookingDraft;
  onBookingSuccess: (action: AgentAction) => void;
}) {
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    dob: "",
    notes: ""
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/booking", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...draft, ...form })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Booking failed");
      onBookingSuccess(data.action);
    } catch (bookingError) {
      setError(
        bookingError instanceof Error
          ? bookingError.message
          : "Không tạo được ticket."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="booking-form" onSubmit={submit}>
      <TicketPreview slot={slot} />
      <div className="form-grid">
        <label>
          Họ tên
          <input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label>
          Số điện thoại
          <input required value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
        </label>
        <label>
          Email
          <input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
        </label>
        <label>
          Ngày sinh
          <input required type="date" value={form.dob} onChange={(event) => setForm({ ...form, dob: event.target.value })} />
        </label>
      </div>
      <label>
        Ghi chú
        <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
      </label>
      {error ? <p className="form-error">{error}</p> : null}
      <button className="primary-action" disabled={isSubmitting} type="submit">
        {isSubmitting ? "Đang tạo ticket..." : "Tạo ticket"}
      </button>
    </form>
  );
}

function TicketPreview({ slot }: { slot: EnrichedSlot }) {
  return (
    <div className="ticket-preview">
      <strong>{slot.specialty_name}</strong>
      <span>{slot.doctor_title} {slot.doctor_name}</span>
      <span>{slot.time} · {formatDate(slot.date)} · {slot.facility_name}</span>
    </div>
  );
}

function detectPii(text: string) {
  return Object.values(piiPatterns).some((pattern) => pattern.test(text));
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(`${date}T00:00:00`));
}
