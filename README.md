# ShopPilot BD

Multi-tenant SaaS for Bangladeshi Facebook-based sellers (boutiques, clothing shops). It covers products, customers, orders, delivery status, reports and customer messaging through the **official Meta WhatsApp Cloud API**, all in one dashboard.

| Layer | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, httpx |
| Database | PostgreSQL 16 |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS |
| Infra | Docker, Docker Compose |

## Quick start (Docker)

```bash
cp .env.example .env          # then set SECRET_KEY (and Meta values when you have them)
docker compose up --build
```

- UI: http://localhost:3000. Register, create your shop, and you are on a 14-day trial.
- API docs (OpenAPI/Swagger): http://localhost:8000/api/docs
- Migrations and plan seeding run automatically when the backend container starts.

If port 8000 or 3000 is already in use, set `BACKEND_PORT` / `FRONTEND_PORT` in `.env`.

Create a platform administrator (needed to activate paid subscriptions):

```bash
docker compose exec backend python -m app.cli create-superuser --email you@example.com --name "Admin" --password 'strong-pass-123'
```

## Running tests

```bash
# Backend: fast, in-memory SQLite, every Meta call mocked
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt   # (bin/ on Linux/macOS)
.venv/Scripts/python -m pytest

# Backend against PostgreSQL, inside Docker
docker compose --profile test run --rm --build backend-tests

# Frontend type check + production build
cd frontend && npm ci && npm run typecheck && npm run build
```

Automated tests **never** call Meta. The opt-in live tests in `backend/tests/manual/` send a real `hello_world` template and only run with `RUN_META_LIVE_TESTS=1` (see [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md#7-manual-live-test)).

## Local development without Docker

```bash
# 1. PostgreSQL
docker compose up -d db
# 2. Backend
cd backend
export DATABASE_URL=postgresql+psycopg://shoppilot:shoppilot@localhost:5432/shoppilot   # or put it in backend/.env
alembic upgrade head && python -m app.cli seed-plans
uvicorn app.main:create_app --factory --reload --port 8000
# 3. Frontend (proxies /api and /media to BACKEND_INTERNAL_URL, default http://localhost:8000)
cd frontend && npm install && npm run dev
```

With `db` only, expose Postgres to the host by adding `ports: ["5432:5432"]` to the `db` service.

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Clean-architecture layers, repository structure, data model, key design decisions |
| [docs/API.md](docs/API.md) | Endpoint reference and example `curl` requests |
| [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md) | Meta app, test number, webhook, templates, consent rules |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deploying to a VPS with HTTPS, backups, operations |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors and Meta error codes |
| [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) | Readiness checklist before the pilot launch |

## What is implemented (phases 1–6)

- **Auth & tenancy**: registration, login, logout, password reset (token emailed; logged to the console in dev), shops, owner/admin/staff roles. Tenant isolation is enforced in the repository layer, and a forged `X-Business-Id` header returns 404.
- **Products**: CRUD, archive/restore, search, size/colour variants with stock and low-stock thresholds, image upload (validated by file signature), CSV import/export.
- **Customers**: E.164 phone normalization with duplicate detection per shop, order history, and an append-only WhatsApp consent log.
- **Orders**: atomic creation (row-locked stock reservation and order numbers), Decimal money, delivery charge, discount, configurable payment methods, a status workflow with an audit history, restocking on cancel/return, and recorded payments.
- **Dashboard & reports**: today's numbers, pending confirmations, status counts, low stock, recent activity, WhatsApp delivery stats, and a date-range sales report. Gross order value, collected revenue and estimated profit are kept separate.
- **WhatsApp**:
  - **Settings page**: connection checks, masked token, webhook status, recent API errors, test-recipient list.
  - **Sending**: text and template sends with idempotency keys. Sends are never auto-retried, and timeouts are marked `unknown`.
  - **Order notifications**: always previewed before sending, with consent, 24-hour window and test-recipient rules enforced on the server.
  - **Webhooks**: signature-verified and deduplicated; status updates only move forward.
  - **Inbox**: polling refresh and replies, allowed only while the 24-hour window is open.
  - **Opt-out**: customers who reply STOP are opted out automatically.
- **Subscriptions**: Trial / Starter ৳499 / Growth ৳999 plans, with limits stored on the plan rows. Usage is recorded, activation is manual by an admin, and the API returns an explicit `is_paid` flag.

See [Known limitations](docs/ARCHITECTURE.md#known-limitations) for what is intentionally left for later phases.
