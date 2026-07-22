# Architecture

## Overview

AutoTracker is a two-tier app: a **FastAPI** backend (API + background workers)
and a **React/Vite** SPA served by nginx. State lives in a SQL database
(SQLite by default, Postgres-ready) and an S3-compatible object store (MinIO).

## Backend layering

```
api/routes/*        HTTP endpoints (thin) — validation, auth, orchestration
  └─ api/deps.py    DI: db session, current user, vehicle access control
schemas/*           Pydantic v2 request/response contracts
services/*          Business logic that isn't HTTP-specific
  ├─ storage.py     object storage (MinIO ↔ local fallback)
  ├─ alerts.py      expiry alert generation + delivery
  ├─ scheduler.py   APScheduler wiring for the daily sweep
  ├─ fuel_stats.py  full-to-full mileage recomputation
  ├─ telegram_bot.py  bot lifecycle + handlers (background thread)
  ├─ notifications.py delivery to Telegram
  └─ audit.py       audit-log helper
ocr/*               Tesseract engine + classification + regex field parsers
models/*            SQLAlchemy 2.0 ORM (typed Mapped columns)
```

### Request → storage flow (document upload)

1. `POST /api/vehicles/{id}/documents` receives a multipart file.
2. If `auto_ocr`, `ocr.extract_text()` rasterises (pdf2image) and OCRs
   (pytesseract) the file.
3. `ocr.classify_document()` scores keyword sets to pick a `DocumentType`.
4. `ocr.parse_fields()` extracts expiry/issue dates, document numbers, issuer,
   registration/VIN via regex — doc-type-aware.
5. Bytes are persisted via `services.storage` (MinIO, else local disk).
6. A `Document` row is written; manual form fields override OCR guesses.

### Access control

`api/deps.py` centralises authorization:

- `get_current_user` — JWT bearer, or the built-in owner in `SINGLE_USER` mode.
- `get_accessible_vehicle` — owner **or** a member of the vehicle's family.
- `require_vehicle_write` — same, but blocks family `viewer`s from mutating.

Document/service/fuel endpoints resolve their parent vehicle through these, so
authorization is defined once.

### Background work

- **Scheduler** (`services/scheduler.py`): a `BackgroundScheduler` runs
  `alerts.run_sweep` daily at `ALERT_SWEEP_HOUR` and once at boot. The sweep
  finds current documents expiring within the max lead window, creates a single
  de-duplicated `Alert` per (document, threshold), then delivers pending alerts.
- **Telegram bot** (`services/telegram_bot.py`): runs in a daemon thread with
  its own asyncio loop so it coexists with uvicorn. Disabled cleanly when no
  token is configured.

## Data model

```
User ──< Vehicle ──< Document (versioned via supersedes_id)
             │   └──< ServiceRecord
             │   └──< FuelLog (distance/efficiency computed)
             │   └──< AccidentRecord
             └── Family (optional share)

Family ──< FamilyMembership (role) ──> User
       └──< FamilyInvite (code, role, uses, expiry)

Alert (per user/document/threshold, de-duped)
AuditLog (actor, family, action, entity)
```

## Fuel efficiency

`services/fuel_stats.recompute()` recomputes the whole vehicle chain on every
insert/update/delete (so out-of-order entry is fine). For each full-tank fill
after the first, `efficiency = distance-since-last-full-tank / fuel-used`,
summing quantities of any intervening partial fills.

## Scaling / production notes

- Swap `DATABASE_URL` to Postgres and add Alembic migrations.
- Point `S3_*` at AWS S3 / Cloudflare R2 (`S3_SECURE=true`); presigned URLs are
  already used for downloads when the backend supports them.
- Run the Telegram bot as its own process/replica for horizontal scaling.
- Put the API behind a reverse proxy; the SPA already same-origin-proxies `/api`.
