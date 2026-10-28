# Troubleshooting

## Application

| Symptom | Cause / fix |
|---|---|
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Another service uses the port. Set `BACKEND_PORT=8010` (or `FRONTEND_PORT`) in `.env`. |
| `403 CSRF token missing or invalid` | A cookie-based request without the `X-CSRF-Token` header. Use the frontend API client, or a Bearer token for scripts. Sign in again if the `sp_csrf` cookie is missing. |
| `400 X-Business-Id header is required` | The active shop is not selected. Sign out and in again, or set the header when calling the API. |
| `404` for a record that exists | It belongs to a different shop than the `X-Business-Id` you sent. This is tenant isolation working as intended. |
| `402 plan_limit_exceeded` | The monthly order or message limit was reached, or the trial expired. Upgrade under **Subscription**; an admin activates it after payment. |
| `422 insufficient_stock` | Update the variant stock on the product page. |
| `409 duplicate_customer` | The phone number (after normalization) already exists. Open the existing customer from the error. |
| Login works but every page redirects to `/login` | When serving over plain HTTP with `COOKIE_SECURE=true`, browsers drop the cookie. Use HTTPS or set it to false locally. |
| Frontend shows "Cannot reach the server" | The backend is down, or `BACKEND_INTERNAL_URL` was wrong at **build time** (rewrites are baked into the build). Rebuild the frontend image. |
| `Unsafe production configuration` on start | Set a real `SECRET_KEY` and `COOKIE_SECURE=true`. |
| Password reset email never arrives | In this version the reset link is printed in the backend logs: `docker compose logs backend \| grep reset-password`. |

## WhatsApp

| Symptom | Cause / fix |
|---|---|
| Settings shows **Not connected** and the connect button is disabled | `META_ACCESS_TOKEN` / `META_PHONE_NUMBER_ID` are not set in the backend environment. Restart after editing `.env`. |
| **Connection check failed**, error kind `auth`, code `190` | The access token expired (temporary tokens last 24 hours) or is invalid. Generate a new one, or use a System User permanent token. |
| `409 phone_number_in_use` | The test number is already linked to another shop. Disconnect it there first. |
| Webhook "Verify and save" fails in Meta | The URL is not public HTTPS or does not end in `/webhooks/whatsapp/`, the `META_VERIFY_TOKEN` differs, or the tunnel points at the frontend port instead of the backend port. |
| Incoming messages don't appear | Check that the `messages` webhook field is subscribed. Check the backend logs for `invalid signature` (wrong `META_APP_SECRET`). The phone number ID in the payload must be connected to a shop. Otherwise the event is ignored. |
| `422 … 24-hour customer service window is closed` | Free text can only be sent within 24 hours of the customer's last message. Use an approved template. |
| `422 … No WhatsApp opt-in is recorded` | Record the customer's consent on their page. |
| `422 Test mode: this number is not an authorized test recipient` | Add the number in Meta **API Setup → To** *and* in ShopPilot **WhatsApp Settings**. |
| Message status stays **delivery unknown** | The request to Meta timed out, so the message may or may not have been sent. Wait for a webhook status. Do not resend blindly. |
| Status stays **accepted** forever | Webhook status events are not arriving. See the webhook rows above. |

### Common Meta error codes

| Code | Meaning | What to do |
|---|---|---|
| 190 | Access token expired or invalid | New token / permanent system-user token |
| 10, 200 | Permission missing | Give the token `whatsapp_business_messaging` permission |
| 4, 80007, 130429 | Rate limit | Wait and retry later (never automatically) |
| 131030 | Recipient not in the allowed list (test number) | Add the recipient in Meta API Setup |
| 131047 | Re-engagement required (more than 24 hours since the last customer message) | Send an approved template |
| 131026 | Message undeliverable (not a WhatsApp user, old app, …) | Contact the customer another way |
| 131056 | Too many messages to the same user | Slow down |
| 132000–132069 | Template problems (wrong name, language, parameter count, not approved) | Check the template name, language and number of `{{n}}` placeholders |
| 133010 | Phone number not registered | Register the number in WhatsApp Manager |

Each failure appears under **WhatsApp Settings → Recent API errors** with the `fbtrace_id`. Quote that ID when contacting Meta support.
