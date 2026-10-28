# API reference

Interactive OpenAPI docs: `http://localhost:8000/api/docs` (ReDoc: `/api/redoc`, schema: `/api/openapi.json`).

## Conventions

- **Auth**: either the `sp_session` cookie (browser; unsafe methods need the `X-CSRF-Token` header equal to the `sp_csrf` cookie) or `Authorization: Bearer <token>` from `POST /api/auth/token`.
- **Tenant**: every business-scoped endpoint needs `X-Business-Id: <id>`. Non-members get `404`.
- **Money** is returned as decimal strings (`"1250.00"`) in resource responses. Dashboard and report aggregates are numbers.
- **Errors** always look like this:
  ```json
  {"error": {"code": "insufficient_stock", "message": "Only 1 in stock for Kurti (M / Red).", "details": {"variant_id": 3, "available": 1}}}
  ```
  | HTTP | When |
  |---|---|
  | 401 | not signed in / session expired |
  | 403 | CSRF failure or role not allowed |
  | 404 | not found, or belongs to another business |
  | 409 | duplicate (SKU, customer phone, email), WhatsApp not configured |
  | 402 | plan limit reached or subscription inactive |
  | 413 | body too large |
  | 422 | validation error, invalid status transition, WhatsApp policy violation (`details.reasons`) |
  | 429 | rate limited (ours or Meta's) |
  | 502 | Meta rejected the message, or delivery is unknown after a timeout |

## Endpoints

### Auth
| Method | Path | Notes |
|---|---|---|
| POST | `/api/auth/register` | `{email, password, full_name}` → sets session cookies |
| POST | `/api/auth/login` | `{email, password}` → sets session cookies |
| POST | `/api/auth/token` | `{email, password}` → `{access_token}` for scripts |
| POST | `/api/auth/logout` | clears cookies |
| GET | `/api/auth/me` | user + memberships |
| POST | `/api/auth/password-reset/request` | `{email}` → always 202 |
| POST | `/api/auth/password-reset/confirm` | `{token, new_password}` (signs out all sessions) |

### Business
| Method | Path | Notes |
|---|---|---|
| POST | `/api/businesses` | create shop (caller becomes owner, trial starts) |
| GET / PATCH | `/api/business` | current shop profile (PATCH: owner/admin) |
| GET / POST | `/api/business/members` | list / add an existing user `{email, role}` |
| PATCH / DELETE | `/api/business/members/{id}` | change role (owner) / remove |
| GET / PUT | `/api/business/payment-methods` | list / upsert `{code, label, is_active}` |

### Products
| Method | Path | Notes |
|---|---|---|
| GET | `/api/products?q=&status=active&page=1&page_size=20` | search name/SKU |
| POST | `/api/products` | `{name, sku, price, cost_price?, description?, stock?, variants?: [{size, color, sku?, price?, stock, low_stock_threshold}]}` |
| GET / PATCH | `/api/products/{id}` | |
| POST | `/api/products/{id}/archive`, `/unarchive` | |
| POST | `/api/products/{id}/image` | multipart `file` (JPEG/PNG/WebP ≤ 3 MB) |
| POST / PATCH / DELETE | `/api/products/{id}/variants[/{variant_id}]` | |
| GET | `/api/products/export.csv` | |
| POST | `/api/products/import` | multipart `file`; columns `name,sku,description,price,cost_price,status,variant_sku,size,color,variant_price,stock,low_stock_threshold` |

### Customers
| Method | Path | Notes |
|---|---|---|
| GET | `/api/customers?q=` | name or phone digits |
| POST | `/api/customers` | `409 duplicate_customer` with `details.existing_customer_id` |
| GET | `/api/customers/check-duplicate?phone=01712345678` | |
| GET / PATCH | `/api/customers/{id}` | detail includes orders and consent history |
| POST | `/api/customers/{id}/consents` | `{purpose: transactional\|marketing, status: granted\|revoked, source, note?}` |

### Orders
| Method | Path | Notes |
|---|---|---|
| GET | `/api/orders?q=&status=&customer_id=&date_from=YYYY-MM-DD&date_to=` | dates in Asia/Dhaka |
| POST | `/api/orders` | see example below |
| GET / PATCH | `/api/orders/{id}` | PATCH: `shipping_address`, `note` |
| POST | `/api/orders/{id}/status` | `{status, note?}` |
| POST | `/api/orders/{id}/payments` | `{amount, method_code?, reference?}` |
| GET | `/api/orders/{id}/notifications/preview?kind=order_confirmed` | `kind`: `order_confirmed`, `order_shipped`, `order_delivered`, `custom` (+`custom_text`) |
| POST | `/api/orders/{id}/notifications` | `{kind, custom_text?}` + `Idempotency-Key` header |

### Dashboard & reports
| Method | Path |
|---|---|
| GET | `/api/dashboard` |
| GET | `/api/reports/sales?date_from=&date_to=` (default: last 30 days, max 366) |

### WhatsApp
| Method | Path | Notes |
|---|---|---|
| GET | `/api/whatsapp/settings` | status, masked token, webhook, templates, test recipients, recent errors |
| POST | `/api/whatsapp/settings/connect` | link the env test number to this shop + run check |
| POST | `/api/whatsapp/settings/check` | re-run the Graph API check |
| POST | `/api/whatsapp/settings/disconnect` | |
| POST / DELETE | `/api/whatsapp/test-recipients[/{id}]` | |
| POST | `/api/whatsapp/messages/send/` | `{to\|customer_id\|conversation_id, text, order_id?}`. 24h window only |
| POST | `/api/whatsapp/messages/send-template/` | `{to\|customer_id, template_name, language, body_parameters[], order_id?}`. Needs opt-in |
| GET | `/api/whatsapp/conversations?unread_only=` | |
| GET | `/api/whatsapp/conversations/{id}` | marks read; includes `can_reply` and `reply_blockers` |
| POST | `/api/whatsapp/conversations/{id}/reply` | `{text}` + `Idempotency-Key` |
| GET | `/api/whatsapp/stats?days=30` | |
| GET | `/webhooks/whatsapp/` | Meta verification (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| POST | `/webhooks/whatsapp/` | Meta events; requires valid `X-Hub-Signature-256` |

### Subscription
| Method | Path | Notes |
|---|---|---|
| GET | `/api/subscription` | current plan, `is_paid`, usage, public plans |
| POST | `/api/subscription/request` | `{plan_code}` → records the request only (not paid) |
| GET | `/api/admin/subscriptions` | superuser |
| POST | `/api/admin/businesses/{id}/subscription/activate` | superuser: `{plan_code, months, payment_reference, notes?}` |

## Example requests

```bash
API=http://localhost:8000
TOKEN=$(curl -s -X POST $API/api/auth/token -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"demo12345"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
H=(-H "Authorization: Bearer $TOKEN" -H "X-Business-Id: 1" -H 'Content-Type: application/json')

# Product with two sizes
curl -s "${H[@]}" -X POST $API/api/products -d '{
  "name":"Cotton Kurti","sku":"KURTI-1","price":"1190","cost_price":"700",
  "variants":[{"size":"M","color":"Red","stock":5},{"size":"L","color":"Red","stock":3}]}'

# Order for a new (or existing, matched by phone) customer
curl -s "${H[@]}" -X POST $API/api/orders -d '{
  "new_customer":{"name":"Rahim","phone":"01812-345678","address":"House 4, Road 2, Mirpur 10, Dhaka"},
  "items":[{"variant_id":1,"quantity":1}],
  "delivery_charge":"60","discount":"0","payment_method_code":"cod"}'

# Confirm it and record COD collection after delivery
curl -s "${H[@]}" -X POST $API/api/orders/1/status -d '{"status":"confirmed","note":"Called customer"}'
curl -s "${H[@]}" -X POST $API/api/orders/1/payments -d '{"amount":"1250","method_code":"cod"}'

# Record WhatsApp opt-in, preview and send the confirmation template
curl -s "${H[@]}" -X POST $API/api/customers/1/consents -d '{"status":"granted","source":"facebook","note":"Agreed in Messenger"}'
curl -s "${H[@]}" "$API/api/orders/1/notifications/preview?kind=order_confirmed"
curl -s "${H[@]}" -H "Idempotency-Key: order-1-confirm" -X POST $API/api/orders/1/notifications -d '{"kind":"order_confirmed"}'

# Generic template send (test number's built-in template)
curl -s "${H[@]}" -H "Idempotency-Key: $(uuidgen)" -X POST $API/api/whatsapp/messages/send-template/ \
  -d '{"to":"01812345678","template_name":"hello_world","language":"en_US"}'

# Simulate a signed webhook locally (META_APP_SECRET must match)
BODY='{"object":"whatsapp_business_account","entry":[{"changes":[{"field":"messages","value":{"metadata":{"phone_number_id":"'$META_PHONE_NUMBER_ID'"},"contacts":[{"wa_id":"8801812345678","profile":{"name":"Rahim"}}],"messages":[{"from":"8801812345678","id":"wamid.TEST1","timestamp":"'$(date +%s)'","type":"text","text":{"body":"Price koto?"}}]}}]}]}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$META_APP_SECRET" | sed 's/^.* //')
curl -s -X POST $API/webhooks/whatsapp/ -H "X-Hub-Signature-256: sha256=$SIG" -H 'Content-Type: application/json' -d "$BODY"
```
