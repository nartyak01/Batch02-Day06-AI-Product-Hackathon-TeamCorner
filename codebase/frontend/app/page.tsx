"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type {
  AgentAction,
  BookingDraft,
  ChatMessage,
  Booking,
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
    "Xin chào, mình là trợ lý đặt lịch VinmecCare. Bạn đang gặp triệu chứng gì và muốn khám ở khu vực nào?"
};

export default function Home() {
  const [messages, setMessages] = useState<UiMessage[]>([initialAssistant]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"chat" | "tickets">("chat");
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [clarifyingQuestionsAsked, setClarifyingQuestionsAsked] = useState(0);
  const [ticketFilters, setTicketFilters] = useState({
    ticketId: "",
    name: "",
    phone: "",
    email: "",
    dob: "",
    status: ""
  });
  const [ticketResults, setTicketResults] = useState<Booking[]>([]);
  const [ticketError, setTicketError] = useState("");
  const [ticketLoading, setTicketLoading] = useState(false);
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
    scrollToBottom();
  }, [messages, isLoading]);

  function scrollToBottom() {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth"
    });
  }

  function handleTabChange(tab: "chat" | "tickets") {
    setActiveTab(tab);
    if (tab === "chat") {
      setTicketError("");
    }
  }

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
          messages: nextMessages.map(({ role, content }) => ({ role, content })),
          context: {
            clarifying_questions_asked: clarifyingQuestionsAsked
          }
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Agent error");
      pushAssistant(data.action.message, data.action);
      setClarifyingQuestionsAsked((current) =>
        data.action?.type === "ask_clarifying_question" ? Math.min(current + 1, 2) : 0
      );
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
          status: "draft",
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

  async function searchTickets(event: FormEvent) {
    event.preventDefault();
    const hasCriteria = Object.values(ticketFilters).some((value) => value.trim().length > 0);
    if (!hasCriteria) {
      setTicketError("Nhập ít nhất một thông tin để tra cứu.");
      setTicketResults([]);
      return;
    }

    setTicketLoading(true);
    setTicketError("");
    try {
      const params = new URLSearchParams();
      if (ticketFilters.ticketId.trim()) params.set("ticket_id", ticketFilters.ticketId.trim());
      if (ticketFilters.name.trim()) params.set("name", ticketFilters.name.trim());
      if (ticketFilters.phone.trim()) params.set("phone", ticketFilters.phone.trim());
      if (ticketFilters.email.trim()) params.set("email", ticketFilters.email.trim());
      if (ticketFilters.dob.trim()) params.set("dob", ticketFilters.dob.trim());
      if (ticketFilters.status.trim()) params.set("status", ticketFilters.status.trim());

      const response = await fetch(`/api/booking?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Booking lookup error");
      setTicketResults(Array.isArray(data.bookings) ? data.bookings : []);
    } catch (lookupError) {
      setTicketError(
        lookupError instanceof Error
          ? lookupError.message
          : "Không tra cứu được ticket."
      );
      setTicketResults([]);
    } finally {
      setTicketLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="context-panel">
          <div className="brand-lockup">
            <div className="brand-mark">V</div>
            <div>
              <p className="eyebrow">VinmecCare</p>
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
            <div className="tab-switcher">
              <button
                className={activeTab === "chat" ? "tab-pill active" : "tab-pill"}
                type="button"
                onClick={() => handleTabChange("chat")}
              >
                Chat
              </button>
              <button
                className={activeTab === "tickets" ? "tab-pill active" : "tab-pill"}
                type="button"
                onClick={() => handleTabChange("tickets")}
              >
                Ticket
              </button>
            </div>
          </header>

          {activeTab === "chat" ? (
            <>
              <div className="chat-scroll-region">
                <div className="messages" ref={scrollRef}>
                  {messages.map((message) => (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      facilities={facilities}
                      specialties={specialties}
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
                <button
                  aria-label="Kéo xuống cuối chat"
                  className="chat-scroll-bottom-button"
                  onClick={scrollToBottom}
                  title="Kéo xuống cuối chat"
                  type="button"
                >
                  ↓
                </button>
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
            </>
          ) : (
            <div className="tickets-panel">
              <form className="ticket-search" onSubmit={searchTickets}>
                <div className="ticket-search-grid">
                  <label>
                    Ticket
                    <input
                      value={ticketFilters.ticketId}
                      onChange={(event) =>
                        setTicketFilters((current) => ({ ...current, ticketId: event.target.value }))
                      }
                      placeholder="VMC-..."
                    />
                  </label>
                  <label>
                    Họ tên
                    <input
                      value={ticketFilters.name}
                      onChange={(event) =>
                        setTicketFilters((current) => ({ ...current, name: event.target.value }))
                      }
                      placeholder="Nguyễn Văn A"
                    />
                  </label>
                  <label>
                    SĐT
                    <input
                      value={ticketFilters.phone}
                      onChange={(event) =>
                        setTicketFilters((current) => ({ ...current, phone: event.target.value }))
                      }
                      placeholder="0xxxxxxxxx"
                    />
                  </label>
                  <label>
                    Email
                    <input
                      value={ticketFilters.email}
                      onChange={(event) =>
                        setTicketFilters((current) => ({ ...current, email: event.target.value }))
                      }
                      placeholder="you@example.com"
                    />
                  </label>
                  <label>
                    Ngày sinh
                    <input
                      type="date"
                      value={ticketFilters.dob}
                      onChange={(event) =>
                        setTicketFilters((current) => ({ ...current, dob: event.target.value }))
                      }
                    />
                  </label>
                  <label>
                    Trạng thái
                    <select
                      value={ticketFilters.status}
                      onChange={(event) =>
                        setTicketFilters((current) => ({ ...current, status: event.target.value }))
                      }
                    >
                      <option value="">Tất cả</option>
                      <option value="confirmed">confirmed</option>
                      <option value="draft">draft</option>
                      <option value="callback">callback</option>
                      <option value="pending_review">pending_review</option>
                      <option value="cancelled">cancelled</option>
                    </select>
                  </label>
                </div>
                {ticketError ? <p className="form-error">{ticketError}</p> : null}
                <div className="ticket-search-actions">
                  <button className="primary-action" disabled={ticketLoading} type="submit">
                    {ticketLoading ? "Đang tra cứu..." : "Tra cứu ticket"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setTicketFilters({
                        ticketId: "",
                        name: "",
                        phone: "",
                        email: "",
                        dob: "",
                        status: ""
                      });
                      setTicketResults([]);
                      setTicketError("");
                    }}
                  >
                    Xóa lọc
                  </button>
                </div>
              </form>

              <div className="ticket-results">
                {ticketResults.length > 0 ? (
                  ticketResults.map((booking) => (
                    <BookingCard
                      key={booking.ticket_id}
                      booking={booking}
                      onBookingUpdated={(updatedBooking) =>
                        setTicketResults((current) =>
                          current.map((item) =>
                            item.ticket_id === updatedBooking.ticket_id ? updatedBooking : item
                          )
                        )
                      }
                    />
                  ))
                ) : (
                  <p className="muted">Chưa có kết quả tra cứu.</p>
                )}
              </div>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function MessageBubble({
  message,
  facilities,
  specialties,
  onConfirmSlot,
  onRenderForm,
  onRefreshSlots,
  onBookingSuccess
}: {
  message: UiMessage;
  facilities: Facility[];
  specialties: Specialty[];
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
  onConfirmSlot,
  onRenderForm,
  onRefreshSlots,
  onBookingSuccess
}: {
  action: AgentAction;
  facilities: Facility[];
  specialties: Specialty[];
  onConfirmSlot: (slot: EnrichedSlot, draft: BookingDraft) => void;
  onRenderForm: (slot: EnrichedSlot, draft: BookingDraft) => void;
  onRefreshSlots: (facilityId: string, specialtyId: string, symptomSummary: string) => void;
  onBookingSuccess: (action: AgentAction) => void;
}) {
  if (action.type === "ask_clarifying_question") {
    const questions = action.questions ?? [];
    if (questions.length === 0) return null;
    return (
      <div className="clarifying-questions">
        {questions.map((question) => (
          <p key={question}>{question}</p>
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

function BookingCard({
  booking,
  onBookingUpdated
}: {
  booking: Booking;
  onBookingUpdated: (booking: Booking) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const [editForm, setEditForm] = useState({
    name: booking.name ?? "",
    phone: booking.phone ?? "",
    email: booking.email ?? "",
    dob: booking.dob ?? "",
    notes: booking.notes ?? ""
  });
  const dateLabel = booking.slot_date
    ? `${formatDate(booking.slot_date)} · ${booking.slot_time || "Chưa rõ giờ"}`
    : "Chưa có lịch hẹn";

  async function patchBooking(patch: Partial<Booking>) {
    setIsSaving(true);
    setActionError("");
    try {
      const response = await fetch(`/api/booking?ticket_id=${encodeURIComponent(booking.ticket_id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? data.message ?? "Update booking error");
      const updatedBooking = data.booking as Booking;
      onBookingUpdated(updatedBooking);
      setEditForm({
        name: updatedBooking.name ?? "",
        phone: updatedBooking.phone ?? "",
        email: updatedBooking.email ?? "",
        dob: updatedBooking.dob ?? "",
        notes: updatedBooking.notes ?? ""
      });
      setIsEditing(false);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Không cập nhật được ticket."
      );
    } finally {
      setIsSaving(false);
    }
  }

  function resetEditForm() {
    setEditForm({
      name: booking.name ?? "",
      phone: booking.phone ?? "",
      email: booking.email ?? "",
      dob: booking.dob ?? "",
      notes: booking.notes ?? ""
    });
    setActionError("");
    setIsEditing(false);
  }

  async function submitEdit(event: FormEvent) {
    event.preventDefault();
    await patchBooking(editForm);
  }

  async function cancelTicket() {
    const confirmed = window.confirm("Bạn chắc chắn muốn hủy ticket này?");
    if (!confirmed) return;
    await patchBooking({ status: "cancelled" });
  }

  return (
    <article className="booking-ticket-card">
      <div className="booking-ticket-head">
        <div>
          <p className="eyebrow">Ticket</p>
          <h3>{booking.ticket_id}</h3>
        </div>
        <span className={`status-chip ${booking.status || "draft"}`}>{booking.status || "draft"}</span>
      </div>
      <div className="booking-ticket-grid">
        <span>
          <strong>Họ tên:</strong> {booking.name || "-"}
        </span>
        <span>
          <strong>SĐT:</strong> {booking.phone || "-"}
        </span>
        <span>
          <strong>Email:</strong> {booking.email || "-"}
        </span>
        <span>
          <strong>Ngày sinh:</strong> {booking.dob || "-"}
        </span>
        <span>
          <strong>Cơ sở:</strong> {booking.facility_name || "-"}
        </span>
        <span>
          <strong>Chuyên khoa:</strong> {booking.specialty_name || "-"}
        </span>
        <span>
          <strong>Bác sĩ:</strong> {booking.doctor_title ? `${booking.doctor_title} ` : ""}
          {booking.doctor_name || "-"}
        </span>
        <span>
          <strong>Giờ khám:</strong> {dateLabel}
        </span>
      </div>
      <p className="booking-ticket-note">
        <strong>Triệu chứng:</strong> {booking.symptom_summary || "-"}
      </p>
      {isEditing ? (
        <form className="ticket-edit-form" onSubmit={submitEdit}>
          <div className="ticket-search-grid">
            <label>
              Họ tên
              <input
                required
                value={editForm.name}
                onChange={(event) =>
                  setEditForm((current) => ({ ...current, name: event.target.value }))
                }
              />
            </label>
            <label>
              SĐT
              <input
                required
                value={editForm.phone}
                onChange={(event) =>
                  setEditForm((current) => ({ ...current, phone: event.target.value }))
                }
              />
            </label>
            <label>
              Email
              <input
                required
                type="email"
                value={editForm.email}
                onChange={(event) =>
                  setEditForm((current) => ({ ...current, email: event.target.value }))
                }
              />
            </label>
            <label>
              Ngày sinh
              <input
                required
                type="date"
                value={editForm.dob}
                onChange={(event) =>
                  setEditForm((current) => ({ ...current, dob: event.target.value }))
                }
              />
            </label>
          </div>
          <label>
            Ghi chú
            <textarea
              value={editForm.notes}
              onChange={(event) =>
                setEditForm((current) => ({ ...current, notes: event.target.value }))
              }
            />
          </label>
          {actionError ? <p className="form-error">{actionError}</p> : null}
          <div className="ticket-card-actions">
            <button className="primary-action" disabled={isSaving} type="submit">
              {isSaving ? "Đang lưu..." : "Lưu thay đổi"}
            </button>
            <button disabled={isSaving} type="button" onClick={resetEditForm}>
              Bỏ qua
            </button>
          </div>
        </form>
      ) : (
        <>
          {booking.notes ? (
            <p className="booking-ticket-note">
              <strong>Ghi chú:</strong> {booking.notes}
            </p>
          ) : null}
          {actionError ? <p className="form-error">{actionError}</p> : null}
          <div className="ticket-card-actions">
            <button type="button" onClick={() => setIsEditing(true)}>
              Sửa ticket
            </button>
            <button
              className="danger-action"
              disabled={isSaving || booking.status === "cancelled"}
              type="button"
              onClick={cancelTicket}
            >
              {booking.status === "cancelled" ? "Đã hủy" : "Hủy ticket"}
            </button>
          </div>
        </>
      )}
    </article>
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
