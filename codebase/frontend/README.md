# Vinmec AI Booking Agent MVP

Prototype frontend for the Vinmec-style AI booking flow.

## Run

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

On Windows PowerShell, use `npm.cmd` if execution policy blocks `npm`:

```powershell
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

## Environment

Create `.env` from `.env.example` and point it to the backend.

```env
BACKEND_API_URL=http://127.0.0.1:8000
```

## Checks

```bash
npm run lint
npm run build
```
