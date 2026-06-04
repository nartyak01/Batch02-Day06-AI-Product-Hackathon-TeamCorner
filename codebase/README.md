# Vinmec AI Booking Agent MVP

Checkpoint 1 prototype for Team Corner: a Vinmec-style AI agent that maps symptoms to an official Vinmec specialty, checks mock slots, asks for confirmation, renders a booking form directly in chat, and stores a ticket in CSV.

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

On Windows PowerShell, use `npm.cmd` if script execution policy blocks `npm`:

```powershell
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

## Environment

Create `.env` from `.env.example`.

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
```

If `GEMINI_API_KEY` is empty or Gemini fails, the prototype falls back to deterministic CSV keyword matching so the demo still works.

## Data

CSV files live in `data/`:

- `facilities.csv`
- `specialties.csv`
- `doctors.csv`
- `slots.csv`
- `bookings.csv`

`specialties.csv` is seeded from Vinmec's official "Chuyên khoa điều trị" page. Doctors and slots are mock data for the hackathon demo.

## Demo Paths

- Happy path: describe symptoms, pick a slot, confirm, submit the inline form, receive a ticket.
- Override path: change facility/specialty in the slot card and reload slots.
- PII guard: phone/email/CCCD typed in chat is blocked before the LLM call.
- Red flag: severe symptoms such as chest pain or trouble breathing trigger hotline/callback instead of normal booking.

## Checks

```bash
npm run lint
npm run build
```
