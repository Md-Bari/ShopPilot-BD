# Production readiness checklist

Tick these off before the Phase 7 pilot with real sellers.

## Security
- [ ] `ENVIRONMENT=production`, a unique random `SECRET_KEY` (≥ 32 chars), `COOKIE_SECURE=true`
- [ ] HTTPS everywhere (reverse proxy with automatic certificates); app ports bound to `127.0.0.1`
- [ ] `CORS_ORIGINS` / `FRONTEND_URL` set to the real domain only
- [ ] Strong `POSTGRES_PASSWORD`; database not exposed publicly
- [ ] `.env` readable only by the deploy user (`chmod 600 .env`) and never committed
- [ ] `META_APP_SECRET` set (webhooks are refused without it) and `META_VERIFY_TOKEN` is random
- [ ] Permanent System User token with the minimum WhatsApp permissions; a token rotation plan exists
- [ ] Superuser accounts limited to the founders, with strong passwords
- [ ] Rate limiting behind the proxy works per client IP (uvicorn runs with `--proxy-headers`; restrict `--forwarded-allow-ips` to the proxy address)

## Data & privacy
- [ ] Daily `pg_dump` backups copied off the server, and one **restore tested**
- [ ] Media volume backed up
- [ ] Daily `purge-webhook-events` cron (default retention 30 days)
- [ ] Privacy notice for sellers: what customer data is stored (name, phone, address, order history, consent log, WhatsApp messages) and why
- [ ] A process to delete or export a customer's data on request
- [ ] Consent is recorded only with real customer agreement (seller training)

## WhatsApp
- [ ] Webhook verified and subscribed to `messages`; a test inbound message appears in the inbox
- [ ] `order_confirmation`, `order_shipped`, `order_delivered` templates approved, and names set in `.env`
- [ ] Test sends to authorized recipients succeed; statuses reach delivered/read
- [ ] Production: verified business, display name approved, `META_MODE=production`, quality rating monitored

## Reliability & operations
- [ ] `docker compose ps` shows all services healthy after a reboot (`restart: unless-stopped`)
- [ ] Monitoring of `GET /api/health` (e.g. UptimeRobot) and disk space
- [ ] Backend logs retained (Docker log rotation configured)
- [ ] Real email adapter for password resets (SMTP / transactional provider) instead of the console logger
- [ ] Manual subscription activation runbook (verify bKash/Nagad transaction → `activate-subscription`)

## Quality
- [ ] `docker compose --profile test run --rm backend-tests` passes on the release commit
- [ ] `npm run typecheck && npm run build` passes
- [ ] Smoke test on a phone: register → shop → product → order → confirm → WhatsApp preview → deliver → record payment → dashboard numbers
- [ ] Pilot plan: 3–5 sellers, a feedback channel, and agreement that pricing (৳499 / ৳999) is a hypothesis
