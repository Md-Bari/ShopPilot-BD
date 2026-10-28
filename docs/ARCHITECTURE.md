# Architecture

## Overview

```
Browser ──► Next.js (3000) ──/api/*, /media/* rewrite──► FastAPI (8000) ──► PostgreSQL
                                                              │
Meta Cloud API ◄──── httpx (MetaCloudApiClient) ──────────────┤
Meta webhooks  ────► POST /webhooks/whatsapp/ (HMAC verified) ┘
```

- The browser only talks to its own origin. Next.js proxies `/api` and `/media` to FastAPI, so the session cookie can be **httpOnly** and no token or WhatsApp credential ever reaches JavaScript.
- Sessions are a signed JWT in an httpOnly `SameSite=Lax` cookie. Unsafe requests also need a **double-submit CSRF token** (`sp_csrf` cookie echoed in `X-CSRF-Token`). API clients can use `POST /api/auth/token` and a `Bearer` header instead, which needs no CSRF token.
- The active shop is sent in `X-Business-Id`. The server verifies membership on every request, and the frontend never filters tenant data itself.

## Backend layers (clean architecture)

```
backend/app/
├── domain/            Pure business rules. No framework, no I/O.
│   ├── enums.py           statuses, roles, consent purposes …
│   ├── errors.py          DomainError hierarchy (mapped to HTTP codes by the API layer)
│   ├── pricing.py         Decimal totals, payment status, estimated profit
│   ├── order_rules.py     allowed status transitions, restock rules
│   ├── messaging_policy.py 24h window, consent, test-recipient rules, status ordering
│   ├── phone.py           E.164 normalization (Bangladesh default)
│   └── clock.py           UTC storage / Asia/Dhaka day boundaries
├── application/       Use cases. Depend on domain + ports, not on FastAPI.
│   ├── ports.py           WhatsAppGateway, CredentialProvider, EmailSender, FileStorage
│   ├── dto.py             validated input commands (also used as request bodies)
│   ├── context.py         TenantContext (user, business, role)
│   ├── auth.py, businesses.py, products.py, customers.py, orders.py,
│   ├── reports.py, subscriptions.py
│   └── whatsapp/          configuration, messaging, notifications, inbox, webhooks, templates
├── infrastructure/    Adapters.
│   ├── db/                SQLAlchemy models, session, UTC datetime type
│   ├── repositories/      tenant-scoped repositories (every query filtered by business_id)
│   ├── whatsapp/          Meta HTTP client, payload builders, signature check, env credentials
│   ├── storage/local.py   product images on a Docker volume
│   └── email/console.py   dev email sender (logs reset links)
├── api/               Delivery layer: routers, response schemas, dependencies, error mapping
├── core/              settings, security helpers, middleware (body-size limit, security headers), rate limiter
├── main.py            application factory = composition root (wires adapters into app.state)
└── cli.py             seed plans, create superuser, activate subscription, purge webhook events
```

Dependency direction: `api → application → domain`, with `infrastructure` implementing the ports. The domain imports nothing from the other layers. External services (Meta, email, file storage) are reached only through the ports, so tests can swap them out (`create_app(..., whatsapp_gateway=..., email_sender=...)`).

**Pragmatic choice:** SQLAlchemy models double as persistence entities, and use cases call concrete tenant-scoped repositories directly instead of going through repository interfaces. That cuts a lot of mapping code for a solo developer. The important rules (money, transitions, messaging policy) still live in the pure `domain` package and are unit tested in isolation.

## Frontend structure

```
frontend/src/
├── app/
│   ├── (auth)/            login, register, forgot/reset password
│   ├── onboarding/        create first shop
│   └── (app)/             authenticated shell: dashboard, orders, products, customers,
│                          inbox, whatsapp/settings, reports, subscription, settings
├── components/ui/         primitives (Button, Input, Card, Badge…), feedback (Modal, ErrorAlert, Pagination…)
├── components/layout/     AppShell with responsive sidebar
├── components/orders/     status badges, WhatsApp NotificationPanel (preview → confirm → send)
└── lib/
    ├── api/client.ts      fetch wrapper: CSRF header, X-Business-Id, ApiError
    ├── api/endpoints.ts   typed API functions per feature (pages never call fetch directly)
    ├── session.tsx        current user + active shop
    ├── i18n.tsx           English / Bangla dictionary
    ├── format.ts          ৳ formatting, Asia/Dhaka dates
    └── hooks.ts           useApi / useAction / useDebounced
```

## Data model

| Area | Tables |
|---|---|
| Identity | `users`, `password_reset_tokens`, `businesses`, `memberships`, `payment_methods` |
| Catalog | `products`, `product_variants` (size/colour, stock ≥ 0 check) |
| Customers | `customers` (unique `business_id + phone`), `customer_communication_consents` (append-only) |
| Orders | `orders` (unique `business_id + order_number`), `order_items` (price snapshot), `order_status_history`, `order_payments` |
| WhatsApp | `whatsapp_configurations` (unique phone_number_id), `whatsapp_test_recipients`, `whatsapp_conversations` (unique `business_id + wa_id`), `whatsapp_messages` (unique `wa_message_id`, unique `business_id + idempotency_key`), `webhook_events` (unique `event_key`), `whatsapp_api_error_logs` |
| Billing | `subscription_plans`, `business_subscriptions`, `usage_records` (unique `business_id + metric + period`) |

All money columns are `NUMERIC(12,2)` and handled as `Decimal`. All timestamps are stored as timezone-aware UTC and converted to Asia/Dhaka for display and for day-based reports.

## Key design decisions

- **Atomic orders**: the use case locks the variant rows (`SELECT … FOR UPDATE`, ordered by id) and the business row (for the next order number). It then checks plan limits, reserves stock and writes the order, items and first history entry in a single transaction.
- **Status workflow**: `pending → confirmed → processing → shipped → delivered`, with `cancelled` (before shipping) and `returned` (after shipping). Cancel and return put stock back. Every change records who made it, when, and an optional note.
- **Revenue honesty**: gross order value excludes cancelled orders. Collected revenue is the sum of recorded payments. Estimated profit counts delivered orders only, as sale − discount − cost.
- **Message deduplication**: an outbound message row is committed as `pending` with its idempotency key *before* Meta is called. A repeated request returns the stored row. Sends are never retried automatically. A timeout becomes `unknown` and the UI blocks an immediate resend.
- **Webhook idempotency**: each message and each status item gets a `webhook_events.event_key` (`message:<wamid>`, `status:<wamid>:<status>`) and is processed in its own savepoint. Status updates only move forward (`sent < delivered < read`; `failed` cannot override delivered or read). Event rows keep a small summary only (no message text or phone numbers) and are purged after `WEBHOOK_EVENT_RETENTION_DAYS`.
- **Credentials**: the MVP uses one Meta test number from environment variables (`SettingsCredentialProvider`). `WhatsAppConfiguration.credential_source` is ready for a per-business encrypted provider later. A shop is only "connected" after a successful Graph API check.
- **Plan limits** live on `subscription_plans` rows. Usage is counted in `usage_records`, and messages are counted only once Meta accepts them.

## Known limitations

- Order items cannot be edited after creation. Cancel and re-create instead (stock is restored).
- Team invitations require the colleague to register first. Invitation emails are not implemented.
- Password-reset emails are written to the backend log (`ConsoleEmailSender`). Plug in an SMTP or transactional-email adapter before the pilot.
- The rate limiter is in-memory, so it is per backend process. Use Redis when running multiple instances.
- Product images are stored on a local Docker volume and served publicly by unguessable UUID file names.
- The inbox polls every 20 seconds. There are no websockets yet.
- Incoming media is recorded as metadata only (no download). Location coordinates are not stored.
- Only one Meta phone number (from env) can be linked, to one shop at a time. Per-business numbers come in a later phase.
- Subscription payments are manual (an admin records the bKash/Nagad reference). There is no payment gateway yet.
- Bangla translation covers navigation, statuses and key dashboard and order labels, not every string.
