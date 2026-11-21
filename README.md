# PorsAI Voice Agent — Sunrise Salon

A starter implementation for the PorsAI take-home assignment. It includes:
- Browser call page using LiveKit WebRTC
- FastAPI backend and PostgreSQL persistence
- Appointment availability, booking, rescheduling and cancellation
- Database-level protection against two bookings for the same stylist/slot
- Sunrise Salon seed data and business FAQs
- LiveKit Agents worker with a Groq-hosted open-weight LLM

> This is a runnable foundation, not a claim that the hosted system is already deployed or fully load-tested. You must add your own credentials, run it, test it, deploy it, and measure voice latency before submission.

## Stack
- Frontend: React + Vite + LiveKit Components
- API: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Realtime audio: LiveKit
- LLM: Groq API serving an open-weight model (default `llama-3.3-70b-versatile`)
- Voice worker: LiveKit Agents; local STT/TTS adapters are intentionally isolated so you can configure open-source Whisper and Piper/Kokoro for your environment.

## Requirements
- Python 3.11+
- Node.js 20+
- Docker + Docker Compose
- LiveKit project (Cloud free tier or self-hosted)
- Groq API key

## Run locally
1. Copy `.env.example` to `.env` and fill in keys.
2. Start PostgreSQL and API:
   ```bash
   docker compose up --build
   ```
3. In another terminal, run the web app:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Open `http://localhost:5173`.

The API automatically creates tables and seeds Sunrise Salon on startup.
The LiveKit token endpoint is `POST /api/livekit/token`. The frontend requests a token and joins the room.

## Run the voice worker
Install worker dependencies in a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-worker.txt
python agent/worker.py dev
```
Configure `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `GROQ_API_KEY`.

### Open-source speech models
The worker is structured around LiveKit Agents. For the assignment, use local/open model adapters for both speech directions:
- STT: faster-whisper (`small` or `base`) on your own machine/server.
- TTS: Piper or Kokoro locally.
Do not replace these with closed speech APIs. The worker's model adapter section is clearly marked; verify compatibility with your installed LiveKit Agents version and document the exact model/runtime you use.

## API
- `GET /api/business`
- `GET /api/services`
- `GET /api/availability?service_id=...&date=YYYY-MM-DD`
- `POST /api/bookings`
- `PATCH /api/bookings/{booking_id}/reschedule`
- `POST /api/bookings/{booking_id}/cancel`
- `POST /api/livekit/token`

## Double-booking protection
PostgreSQL has a unique constraint on `(stylist_id, starts_at)`. Booking writes are committed inside a transaction. If two callers race for the same slot, only one insert succeeds; the other receives HTTP 409. Never rely only on an LLM check for availability.

## Before submission checklist
- [ ] Configure open-source STT and TTS and verify interruption/barge-in in real calls.
- [ ] Add authentication or unguessable booking references for customer self-service actions.
- [ ] Add tests for simultaneous booking attempts and reschedule collisions.
- [ ] Measure at least 20 voice turns and report median and p95 time-to-first-audio.
- [ ] Deploy API, worker, frontend, and database; provide a public call URL.
- [ ] Record the required demo and create the salon-owner handover note.
- [ ] Explain every line of code you submit.

## Notes
The demo seed uses the assignment's Sunrise Salon details, timezone `Asia/Kolkata`, 30-minute slots, stylist schedules, services, policies and FAQs. Booking endpoints require the caller to provide a name and phone number; the API does not reveal other customers' records.
