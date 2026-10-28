# Meta WhatsApp Cloud API setup

ShopPilot BD uses the **official** Cloud API (`graph.facebook.com`). The first release works with Meta's free developer test number.

## 1. Create the Meta app

1. Go to https://developers.facebook.com/apps, create an app of type **Business**, and add the **WhatsApp** product.
2. Under **WhatsApp → API Setup** you get:
   - a **test phone number**: copy its **Phone number ID** to `META_PHONE_NUMBER_ID`.
   - the **WhatsApp Business Account ID**: copy it to `META_WABA_ID`.
   - a **temporary access token** (valid for 24 hours): copy it to `META_ACCESS_TOKEN`.
3. In **App settings → Basic**, copy the **App secret** to `META_APP_SECRET`. It is used to verify webhook signatures.
4. Choose any long random string and put it in `META_VERIFY_TOKEN`.
5. Set `META_GRAPH_API_VERSION` (for example `v21.0`) and `META_MODE=test`.

For anything beyond a quick test, create a **System User** in Business Settings and give it a **permanent token** with the `whatsapp_business_messaging` and `whatsapp_business_management` permissions. Temporary tokens expire after 24 hours and then cause `190` errors.

Restart the backend after changing `.env` (`docker compose up -d backend`).

## 2. Authorized test recipients

The test number can only message up to **5 phone numbers** that you add under **API Setup → To**. Each recipient has to confirm with a code sent to their WhatsApp.

Add the same numbers in **ShopPilot → WhatsApp Settings → Authorized test recipients**. In test mode the server blocks every other number *before* calling Meta. Without this, Meta returns error `131030`.

## 3. Connect the shop

Go to **WhatsApp Settings → Connect test number**. The server links the env phone number ID to your shop and calls `GET /{phone-number-id}`. The shop shows **Connected** only if that check succeeds. Only one shop at a time can use a given phone number ID.

## 4. Webhook

Meta needs a public **HTTPS** URL. For local development, use a tunnel to the backend port:

```bash
cloudflared tunnel --url http://localhost:8000      # or: ngrok http 8000
```

In **WhatsApp → Configuration → Webhook**:
- Callback URL: `https://<your-tunnel-or-domain>/webhooks/whatsapp/`
- Verify token: the value of `META_VERIFY_TOKEN`
- Click **Verify and save**. The settings page then shows "Verified by Meta".
- Under **Webhook fields**, subscribe to **messages**. That one field covers both incoming messages and delivery statuses.

Every POST must carry a valid `X-Hub-Signature-256`, which is an HMAC-SHA256 of the raw body using the app secret. Unsigned or wrongly signed requests get `401`. If `META_APP_SECRET` is empty, all webhooks are refused (`503`).

## 5. Message templates

Outside the 24-hour customer-service window, Meta only delivers **pre-approved templates**. In **WhatsApp Manager → Message templates**, create these templates (category **Utility**, language English):

| Env var | Suggested name | Body (use exactly these placeholders) |
|---|---|---|
| `WA_TEMPLATE_ORDER_CONFIRMED` | `order_confirmation` | `Assalamu Alaikum! Your order #{{1}} has been confirmed. Total: ৳{{2}}. Thank you for shopping with {{3}}.` |
| `WA_TEMPLATE_ORDER_SHIPPED` | `order_shipped` | `Assalamu Alaikum! Your order #{{1}} has been shipped. Amount payable on delivery: ৳{{2}}. Thank you for shopping with {{3}}.` |
| `WA_TEMPLATE_ORDER_DELIVERED` | `order_delivered` | `Assalamu Alaikum! Your order #{{1}} has been delivered. Thank you for shopping with {{2}}.` |

The parameters are filled from the real order: the order number, the total (or the amount still due, for "shipped"), and the shop name.

- Until a template is approved, set its env var to an **empty value**. That notification then falls back to free-form text, which is allowed **only** while the customer's 24-hour window is open.
- The test number ships with an approved `hello_world` template (`language: en_US`, no parameters). You can send it with `POST /api/whatsapp/messages/send-template/`.

## 6. Policy rules enforced by the server

| Rule | Behaviour |
|---|---|
| Free-form text | Only within 24 hours of the customer's last inbound message |
| Business-initiated template | Requires a recorded **opt-in** (`granted` transactional consent) |
| Opt-out | A `revoked` consent blocks all outbound messages. A customer replying `STOP` / `UNSUBSCRIBE` / `বন্ধ` is opted out automatically |
| Test mode | Only authorized test recipients |
| Explicit action | Nothing is sent automatically. Sellers preview, then press **Send now** |
| Order match | e.g. a "shipped" notification needs the order to be in `shipped` status |
| Deduplication | `Idempotency-Key` per send. No automatic retries. A timeout means `unknown` status |

Record consent on the customer page only when the customer really agreed, for example in Messenger chat or on a phone call. Never import numbers in bulk and mark them as opted in.

## 7. Manual live test

```bash
cd backend
RUN_META_LIVE_TESTS=1 META_ACCESS_TOKEN=... META_PHONE_NUMBER_ID=... \
META_TEST_RECIPIENT=8801XXXXXXXXX .venv/Scripts/python -m pytest tests/manual -s
```

This performs a real phone-number lookup and sends `hello_world` to the recipient.

## 8. Moving to production (later phase)

1. Add and verify a real business phone number in WhatsApp Manager, complete business verification, and set a display name.
2. Use a permanent System User token.
3. Set `META_MODE=production`. The test-recipient restriction is then lifted, but consent and window rules still apply.
4. For several shops with their own numbers, implement an encrypted per-business credential provider (`CredentialSource.ENCRYPTED_DATABASE`). The data model and provider port are already in place.
