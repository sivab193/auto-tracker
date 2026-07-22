# 🚗 AutoTracker

**Automobile document & service management portal.** Keep every vehicle's
papers, service history, fuel economy and renewal deadlines in one place — with
OCR that reads your documents for you, a Telegram bot for on-the-go access, and
family sharing so the whole household stays in sync.

<p>
  <img alt="backend" src="https://img.shields.io/badge/backend-FastAPI-009485">
  <img alt="frontend" src="https://img.shields.io/badge/frontend-React%20%2B%20Vite%20%2B%20TS-2563eb">
  <img alt="storage" src="https://img.shields.io/badge/storage-MinIO%20%2F%20S3-c72c48">
  <img alt="ocr" src="https://img.shields.io/badge/OCR-Tesseract-5b8c5a">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

---

## ✨ Features

### Phase 1 — Core (implemented)
- **Vehicle CRUD** — registration, make/model/year, VIN, fuel type, odometer.
- **Document upload with OCR auto-extraction** — Tesseract reads the file, a
  classifier guesses the type (insurance / registration / PUC / …), and
  doc-type-specific regex parsers pull out **expiry dates, policy/registration
  numbers and issuers**. You confirm/edit before saving.
- **Telegram bot** — link your account, browse & fetch documents; sent files
  **auto-delete after a few minutes** and a temporary signed download link is
  offered as a persistent alternative.
- **Expiry-alert scheduler** — a daily sweep (APScheduler) creates alerts at
  configurable lead times (30 / 14 / 7 / 1 days) and delivers them in-app or via
  Telegram. De-duplicated so you're never spammed.
- **Auth, optional** — JWT auth built in from day one, or run in
  `SINGLE_USER=true` mode for a friction-free personal deployment.

### Phase 2 — Service & Fuel (implemented)
- **Service records** with cost, vendor, odometer and next-service reminders.
- **Fuel logs** with **automatic mileage/efficiency** using the full-to-full
  method (handles partial fills correctly).
- **Cost & efficiency analytics** — per-vehicle totals, best/worst economy,
  cost-per-km and a monthly cost breakdown chart.
- **Accident history**.

### Phase 3 — Family Sharing (implemented)
- **Family groups** with shareable **invite codes** (role + usage limits + expiry).
- **Role-based access**: `admin` / `member` / `viewer` (viewers are read-only).
- **Shared vehicles** visible to every member.
- **Full audit log** for accountability.

### Phase 4 — Advanced (scaffolded)
- **Document versioning** — supersede a renewed document; full version history is
  kept and queryable (implemented).
- **PWA** manifest + installable app shell.
- **Multi-language** locale files (`en`, `hi`, …) and a per-user language pref.
- Smart OCR templates & Telegram inline queries — roadmap.

---

## 🏗️ Architecture

```
┌──────────────┐      ┌──────────────────────────────────────────┐
│  React SPA   │─────▶│                FastAPI                    │
│ (Vite + TS)  │ /api │  auth · vehicles · documents · services   │
│   nginx      │◀─────│  fuel · family · alerts · analytics       │
└──────────────┘      │                                           │
                      │  ┌─────────────┐  ┌────────────────────┐  │
                      │  │ OCR pipeline│  │ APScheduler sweep   │  │
                      │  │ Tesseract + │  │ (daily expiry scan) │  │
                      │  │ regex parse │  └────────────────────┘  │
                      │  └─────────────┘  ┌────────────────────┐  │
                      │                   │ Telegram bot thread │  │
                      └───────┬───────────┴─────────┬──────────┘  │
                              │                      │             │
                    ┌─────────▼────────┐   ┌─────────▼─────────┐
                    │ SQLite / Postgres│   │  MinIO / S3 / R2  │
                    │  (SQLAlchemy)    │   │  (object storage) │
                    └──────────────────┘   └───────────────────┘
```

**Design principles**

- **Graceful degradation.** Tesseract, MinIO and the Telegram bot are all
  *optional at runtime* — if a dependency or config is missing the app still
  boots (OCR returns empty, storage falls back to local disk, the bot stays off).
  This makes local dev painless and keeps the container healthy.
- **Storage is swappable.** The MinIO client speaks the S3 API, so moving to AWS
  S3 or Cloudflare R2 is a config change (`S3_ENDPOINT`, `S3_SECURE`), not a
  rewrite.
- **Enum-as-string columns** keep the database human-readable while the ORM
  always hands you real Python enums.

---

## 🚀 Quick start (Docker)

```bash
git clone https://github.com/sivab193/auto-tracker.git
cd auto-tracker
cp .env.example .env          # optional — sensible defaults work as-is
docker compose up --build
```

| Service        | URL                              |
| -------------- | -------------------------------- |
| Frontend       | http://localhost:3000            |
| API + Swagger  | http://localhost:8000/docs       |
| MinIO console  | http://localhost:9001 (minioadmin/minioadmin) |

The stack ships in `SINGLE_USER` mode, so you land straight on the dashboard.

---

## 🧑‍💻 Local development

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload           # http://localhost:8000
pytest -q                                # run the test suite
ruff check app                           # lint
```

> For OCR locally, install the Tesseract binary (`brew install tesseract` /
> `apt install tesseract-ocr poppler-utils`). Without it, uploads still work —
> you just fill document fields in manually.

**Frontend**

```bash
cd frontend
npm install
npm run dev                              # http://localhost:5173 (proxies /api → :8000)
npm run build                            # type-check + production build
```

---

## ⚙️ Configuration

All settings have defaults; see [`.env.example`](.env.example) for the full list.
Highlights:

| Variable                | Default                     | Purpose                                        |
| ----------------------- | --------------------------- | ---------------------------------------------- |
| `SINGLE_USER`           | `true`                      | Bypass auth for a personal deployment          |
| `SECRET_KEY`            | *(change me)*               | JWT signing key                                |
| `DATABASE_URL`          | `sqlite:///./data/…​.db`     | Swap for `postgresql+psycopg://…` in prod       |
| `STORAGE_BACKEND`       | `minio`                     | `minio` (S3-compatible) or `local`             |
| `S3_ENDPOINT` / keys    | `minio:9000` / `minioadmin` | Object storage connection                      |
| `OCR_ENABLED`           | `true`                      | Toggle the Tesseract pipeline                  |
| `TELEGRAM_BOT_TOKEN`    | *(empty)*                   | Set to enable the bot (from @BotFather)        |
| `ALERT_LEAD_DAYS`       | `30,14,7,1`                 | Days-before-expiry to alert                    |
| `ALERT_SWEEP_HOUR`      | `8`                         | Local hour for the daily sweep                 |

---

## 🤖 Telegram bot

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Set `TELEGRAM_BOT_TOKEN` in `.env` and restart the backend.
3. In the app: **Settings → Generate link code**.
4. In Telegram: send `/link <code>` to your bot, then `/docs` to browse & fetch.

Commands: `/start` · `/link <code>` · `/vehicles` · `/docs`.

---

## 🧪 Testing

- **Backend**: `pytest` — vehicle CRUD, document upload + versioning, OCR field
  parsers, fuel mileage math, and the expiry-alert sweep (incl. de-dup).
- **Frontend**: `npm run build` type-checks the whole app under `strict`.
- **CI**: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs lint +
  tests + build on every push/PR.

---

## 📁 Project structure

```
auto-tracker/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py            # app wiring + lifespan (db, scheduler, bot)
│   │   ├── config.py          # pydantic-settings
│   │   ├── models/            # SQLAlchemy ORM
│   │   ├── schemas/           # Pydantic v2 I/O models
│   │   ├── api/routes/        # auth, vehicles, documents, services, fuel, …
│   │   ├── ocr/               # Tesseract engine + doc-type parsers
│   │   └── services/          # storage, alerts, scheduler, telegram, audit
│   └── tests/
└── frontend/
    └── src/
        ├── api/               # typed fetch client + shared types
        ├── context/           # auth
        ├── components/        # Layout, Modal, BarChart
        └── pages/             # Dashboard, Vehicles, VehicleDetail, Family, …
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a deeper dive.

---

## 🗺️ Roadmap

- Smart OCR templates (learn field positions per issuer)
- Telegram inline queries & reminders push
- Offline-first PWA sync
- Postgres + Alembic migrations for multi-user production
- Email alert channel (SMTP)

## 📄 License

MIT — see [LICENSE](LICENSE).
